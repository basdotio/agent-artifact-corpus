import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote, urlparse
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NextcloudWebDAV:
    def __init__(self, base_url: str, user: str, app_password: str):
        self.base_url = base_url.rstrip("/")
        self.user = user
        self.webdav_root = f"{self.base_url}/remote.php/dav/files/{self.user}"
        self.auth = (user, app_password)

    def _url(self, path: str) -> str:
        clean_path = "/" + path.strip("/") if path.strip("/") else ""
        quoted_path = quote(clean_path, safe="/")
        return f"{self.webdav_root}{quoted_path}"

    def list_dir(self, path: str = "/") -> list[str]:
        url = self._url(path) + "/"
        res = requests.request("PROPFIND", url, auth=self.auth, headers={"Depth": "1"}, verify=False)
        if res.status_code != 207:
            return []
        root = ET.fromstring(res.text)
        items = []
        target_path = unquote(urlparse(url).path).rstrip("/") + "/"
        for elem in root.findall(".//{DAV:}response"):
            href = unquote(elem.find("{DAV:}href").text)
            clean_href = href.rstrip("/")
            if clean_href == target_path.rstrip("/"):
                continue
            item_name = clean_href.split("/")[-1]
            if item_name:
                items.append(item_name)
        return items

    def mkdir_p(self, path: str) -> bool:
        parts = [p for p in path.strip("/").split("/") if p]
        cur = ""
        for p in parts:
            cur += "/" + p
            res = requests.request("MKCOL", self._url(cur), auth=self.auth, verify=False)
            if res.status_code not in [201, 405]:
                return False
        return True

    def move(self, src_path: str, dest_path: str, overwrite: bool = False) -> bool:
        src_url = self._url(src_path)
        dest_url = self._url(dest_path)
        headers = {
            "Destination": dest_url,
            "Overwrite": "T" if overwrite else "F"
        }
        res = requests.request("MOVE", src_url, auth=self.auth, headers=headers, verify=False)
        return res.status_code in [201, 204]

    def read_text(self, path: str) -> str:
        res = requests.get(self._url(path), auth=self.auth, verify=False)
        res.raise_for_status()
        return res.text

    def write_text(self, path: str, content: str) -> bool:
        res = requests.put(self._url(path), data=content.encode("utf-8"), auth=self.auth, verify=False)
        return res.status_code in [201, 204]