import http.client
import json

def get_fuel_prices(province_code, base_url="api.opet.com.tr", endpoint="/api/fuelprices/prices", headers=None):
    """
    Fetches fuel prices for a given province code from the Opet API.

    :param province_code: Province code for which fuel prices are requested.
    :param base_url: Base URL of the API (default: 'api.opet.com.tr').
    :param endpoint: API endpoint path (default: '/api/fuelprices/prices').
    :param headers: Optional custom headers for the request. If not provided, default headers will be used.
    :return: Decoded JSON response from the API or an error message if the request fails.
    """
    if headers is None:
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'If-None-Match': '"b39457d5-d652-4bdc-afe3-9cdfe2f06643"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'Cookie': 'ADC_CONN_539B3595F4E=47FCEB89541DADB7BF507A0A76F789E00EB3EAEEED9F1316EACE78F2143039CCAEB9CA535B3BBD08; ADC_REQ_2E94AF76E7=52F80A888B58EE81678CCD7A0BCCC21E2B7E6E0A5F412730E6EF63587E83D32AE1E8A5A19ABF4E7C; ADC_CONN_539B3595F4E=8D99C549A41DADB77BAF2D3E7461DA8ACD7995E73B9B078C3404FE919C5105C4615B2D11EE81F7B7; OPET=rs2|aPakM'
        }

    try:
        conn = http.client.HTTPSConnection(base_url)
        url_with_province = f"{endpoint}?ProvinceCode={province_code}"
        conn.request("GET", url_with_province, '', headers)
        res = conn.getresponse()
        data = res.read()
        return data.decode("utf-8")
    except Exception as e:
        return f"An error occurred: {str(e)}"

def get_json(source_file: str):
    try:
        with open(source_file, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {"error": f"File '{source_file}' not found."}
    except json.JSONDecodeError:
        return {"error": f"Error decoding JSON content from '{source_file}'."}

if __name__ == '__main__':
    print(get_fuel_prices("34"))