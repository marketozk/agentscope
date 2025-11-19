import httpx

CDP_URL = "http://127.0.0.1:9222/json/version"

if __name__ == "__main__":
    try:
        print(f"Requesting {CDP_URL} ...")
        resp = httpx.get(CDP_URL, timeout=3)
        print("Status:", resp.status_code)
        print("Raw text:\n", resp.text[:500])
    except Exception as e:
        print("Error requesting CDP version:", e)
