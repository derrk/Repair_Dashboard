import streamlit as st
from streamlit_tile_grid.TileRenderer import TileGrid

st.set_page_config(page_title="Home", layout="wide")
st.title("Main Repair Dashboard")

st.markdown("Use the sidebar to navigate to other tools like the Warranty Checker.")

title_list = ['Issue Miner Count', 'Hashrate Offline', 'Failure Rate', 'Test Tile']
body_list = ['500', '128 PH/s', 'Test', 'Fail', 'Test']
icon_list = ['bell', 'book', 'people', 'download']

st.title('Tiles')
tile_grid = TileGrid(4)

tile_grid.render(title_list, body_list, icon_list, icon_size='1.5', tile_color='#61dafb', tile_shadow='#4398af', text_color= '#000')
