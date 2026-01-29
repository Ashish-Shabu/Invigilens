import google.generativeai as genai

KEY = "AIzaSyCg-IBkqfZBDXxaRZ4UXm3iwcCU8yUAK0g"
genai.configure(api_key=KEY)

print("Listing Available Models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")
