import os, time, requests, re, uuid, sys

import xml.etree.ElementTree as ET


class UpdateManager:
	def __init__(
		self, device_version=None
	):  # TODO: Patch notes & Hash checking / verification
		self.updates_url = (
			"https://updates.cloud.remarkable.engineering/service/update2"
		)
		self.device_version = device_version if device_version else '3.2.3.1595'
		self.id_lookups = {
			"3.3.2.1666": "ihUirIf133",
			"3.2.3.1595": "fTtpld3Mvn",
			"3.2.2.1581": "dwyp884gLP",
			"3.0.4.1305": "tdwbuIzhYP",
			"2.15.1.1189": "wVbHkgKisg",
			"2.15.0.1067": "lyC7KAjjSB",
			"2.14.3.977": "joPqAABTAW",
			"2.14.3.958": "B7yhC887i1",
			"2.14.3.1047": "RGLmy8Jb39",
			"2.14.3.1005": "4HCZ7J2Bse",
			"2.14.1.866": "JLWa2mnXu1",
			"2.14.0.861": "TfpToxrexR",
			"2.13.0.758": "2N5B5nvpZ4",
			"2.12.3.606": "XOSYryyJXI",
			"2.12.2.573": "XnE1EL7ojK",
			"2.12.1.527": "8OkCxOJFn9",
			"2.11.0.442": "tJDDwsDM4V",
			"2.10.3.379": "n16KxgSfCk",
			"2.10.2.356": "JLB6Ax3hnJ",
		}

		if not os.path.exists("updates"):
			os.mkdir("updates")

		self.latest_version = self.get_latest_version()  
			
		self.latest_toltec_version = "2.15.1.1189" # Crutch
	
	def get_version(self, version=None):
		if version is None:
			version = self.latest_version

		if version not in self.id_lookups:
			return "Not in version list"

		BASE_URL = "https://updates-download.cloud.remarkable.engineering/build/reMarkable%20Device%20Beta/RM110"
		BASE_URL_V3 = "https://updates-download.cloud.remarkable.engineering/build/reMarkable%20Device/reMarkable2"

		if int(version.split(".")[0]) > 2:
			BASE_URL = BASE_URL_V3

		id = f"-{self.id_lookups[version]}-"

		file_name = f"{version}_reMarkable2{id}.signed"
		file_url = f"{BASE_URL}/{version}/{file_name}"

		return self.download_file(file_url, file_name)
 
	def __get_latest_toltec_supported(self):
		site_body_html = requests.get("https://toltec-dev.org/").text  # or /raw ?
		m = re.search(
			"Toltec does not support OS builds newer than (.*)\. You will soft-brick",
			site_body_html,
		)
		if m is None:
			return None

		return m.group(1).strip()

	def get_latest_version(self):
		data = self._generate_xml_data()

		response = self._make_request(data)

		if response is None:  # or if not response
			return

		file_version, file_uri, file_name = self._parse_response(response)
		
		return file_version

	def _generate_xml_data(self):
		params = {
			"installsource": "scheduler",
			"requestid": str(uuid.uuid4()),
			"sessionid": str(uuid.uuid4()),
			"machineid": "00".zfill(32),
			"oem": "RM100-753-12345",
			"appid": "98DA7DF2-4E3E-4744-9DE6-EC931886ABAB",
			"bootid": str(uuid.uuid4()),
			"current": self.device_version,
			"group": "Prod",
			"platform": "reMarkable2",
		}

		return """<?xml version="1.0" encoding="UTF-8"?>
<request protocol="3.0" version="{current}" requestid="{{{requestid}}}" sessionid="{{{sessionid}}}" updaterversion="0.4.2" installsource="{installsource}" ismachine="1">
	<os version="zg" platform="{platform}" sp="{current}_armv7l" arch="armv7l"></os>
	<app appid="{{{appid}}}" version="{current}" track="{group}" ap="{group}" bootid="{{{bootid}}}" oem="{oem}" oemversion="2.5.2" alephversion="{current}" machineid="{machineid}" lang="en-US" board="" hardware_class="" delta_okay="false" nextversion="" brand="" client="" >
		<updatecheck/>
	</app>
</request>""".format(
			**params
		)

	def _make_request(self, data):
		tries = 1

		while tries < 3:
			tries += 1

			response = requests.post(self.updates_url, data)

			if response.status_code == 429:
				print("Too many requests sent, retrying after 20")
				time.sleep(20)

				continue

			response.raise_for_status()

			break

		return response.text

	@staticmethod
	def _parse_response(resp):
		xml_data = ET.fromstring(resp)

		if "noupdate" in resp or xml_data is None:  # Is none?
			return None  # Or False maybe?

		file_name = xml_data.find("app/updatecheck/manifest/packages/package").attrib[
			"name"
		]
		file_uri = (
			f"{xml_data.find('app/updatecheck/urls/url').attrib['codebase']}{file_name}"
		)
		file_version = xml_data.find("app/updatecheck/manifest").attrib["version"]

		return file_version, file_uri, file_name

	@staticmethod
	def download_file(uri, name): # Credit to https://stackoverflow.com/questions/15644964/python-progress-bar-and-downloads
		with open(f"updates/{name}", "wb") as f:
		    response = requests.get(uri, stream=True)
		    total_length = response.headers.get('content-length')

		    if total_length is None: # no content length header, TODO: Error handling & Hash checking
		        f.write(response.content)
		    else:
		        dl = 0
		        total_length = int(total_length)
		        for data in response.iter_content(chunk_size=4096):
		            dl += len(data)
		            f.write(data)
		            done = int(50 * dl / total_length)
		            sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50-done)) )    
		            sys.stdout.flush()
		print(end='\r')
		return name
