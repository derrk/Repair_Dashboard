import streamlit as st

st.set_page_config(page_title="Bitmain Warranty Checker", layout="centered")

import requests
from datetime import time
import pandas as pd 
import time


# --- Streamlit UI ---


st.title(" Bitmain Warranty Checker")

st.markdown("Paste Serial Numbers Manually or Upload a CSV file with a 'serial' column")


def check_warranty(sn):
    url = 'https://shop-repair.bitmain.com/api/warranty/getWarranty'
    params = {'serialNumber': sn.strip()}

    try:
        response = requests.get(url, params=params, timeout=10)

        # ✅ Diagnostic: show raw HTTP status and content
        print(f"\nSerial: {sn}")
        print(f"Status Code: {response.status_code}")
        print(f"Raw Response Text: {response.text[:300]}")  # limit output for readability

        # Ensure server responded with content
        if not response.content:
            return {'serial': sn, 'error': "Empty response (possible rate limiting)"}

        # Attempt to parse JSON
        data = response.json()

        if data.get('warranty') is not None:
            return {
                'serial': sn,
                'days_left': data.get('warranty'),
                'end_date': data.get('warrantyEndDate')
            }
        else:
            return {
                'serial': sn,
                'error': f"Unexpected response: {data.get('message', 'No message')}"
            }
    except Exception as e:
        return {
            'serial': sn,
            'error': f"Request failed: {str(e)}"
        }




# Text input or File Upload 
serials = []

col1, col2 = st.columns(2)

with col1: 
    serial_text = st.text_area("Enter Serial Numbers (one per line): ")
    if serial_text:
        serials.extend([s.strip() for s in serial_text.splitlines() if s.strip()])
with col2:
    uploaded_file = st.file_uploader("Or Upload CSV with 'serial' Column", type=['csv'])
    if uploaded_file is not None:
        df_uploaded = pd.read_csv(uploaded_file)
        if 'serial' in df_uploaded.columns:
            serials.extend(df_uploaded['serial'].astype(str).to_list())
        else:
            st.error("Uploaded file must contain a 'serial' column.")

# --- Check Button --- #
if st.button('Check Warranty') and serials:
    results = []
    st.info(f"Checking {len(serials)} serial numbers. Please Wait...")

    progress_bar = st.progress(0)
    for i, sn in enumerate(serials):
        result = check_warranty(sn)
        results.append(result)
        progress_bar.progress((i + 1) / len(serials))
        time.sleep(6)     # avoid api blocking, may be slow but could be much slower 
    df_results = pd.DataFrame(results)
    st.success("Warranty Check Complete!")
    st.dataframe(df_results)

    csv = df_results.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "warranty_results.csv", "text/csv")
else:
    st.warning("Please enter or upload Serial Numbers")

#
# functioning user input from terminal, will accept line by line SN, any amount as far as I am currently aware
# print results in terminal
#

# # --- User Input ---
# print("Paste serial numbers (one per line). Press Enter twice to submit:")
# serial_list = []
# while True:
#     line = input()
#     if not line.strip():
#         break
#     serial_list.append(line.strip())

# # --- Check ---
# print("\nWarranty Check Results:")
# for sn in serial_list:
#     result = check_warranty(sn)

#     if 'error' in result:
#         print(f"{result['serial']}: ERROR - {result['error']}")
#     else:
#         print(f"{result['serial']}: {result['days_left']} days remaining, ends on {result['end_date']}")

#     time.sleep(10)  # Slow down to avoid getting blocked

# # --- Save to CSV using pandas ---
# df = pd.DataFrame(result)
# timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
# csv_filename = f"warranty_results_{timestamp}.csv"
# df.to_csv(csv_filename, index=False)

# print(f"\n✅ Results saved to {csv_filename}")