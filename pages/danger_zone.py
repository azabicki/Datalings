import streamlit as st
import functions.utils as ut
import functions.auth as auth
import functions.database as db

st.set_page_config(page_title="Danger Zone", layout=ut.app_layout)

# auth
auth.login()

# init
ut.default_style()
ut.create_sidebar()

# DANGER-ZONE
with st.container(border=True):
    st.header(":primary[:material/warning: DANGER ZONE :material/warning:]")
    st.subheader("Database Actions")

    @st.dialog("Nuke database", width="small")
    def nuke_db():
        st.markdown("Are your sure to **nuke** the database???")
        ut.h_spacer(2)
        col = st.columns([3, 1])
        with col[0]:
            if st.button(
                "Nope, abort ABORT ABORT!!!",
                type="secondary",
                icon=":material/close:",
                use_container_width=True,
            ):
                st.rerun()
        with col[1]:
            if st.button("boom", type="primary", icon=":material/bomb:"):
                # Nuke database
                db.nuke_database()
                # Initialize database
                db.init_tables()

                st.rerun()

    if st.button(
        "Nuke the database & build from scratch",
        icon=":material/delete:",
        type="primary",
    ):
        nuke_db()
