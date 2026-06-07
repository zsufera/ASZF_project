import streamlit as st


st.set_page_config(page_title="ASZF QnA Agent", layout="wide")
st.title("ÁSZF Q&A Agent — POC")
st.caption("Scaffold nézet. A részletes UI az implementáció következő lépése.")

with st.sidebar:
    st.subheader("Menü")
    page = st.radio("Nézet", ["Inbox", "Szabad bevitel", "Copilot", "Evaluation"])

st.write(f"Aktuális nézet: **{page}**")
