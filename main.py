import streamlit as st

pg = st.navigation(
    [
        home := st.Page(
            "./pages/home.py",
            title="Home",
            icon="🏠"
        ),
        all_events := st.Page(
            "./pages/all_events.py",
            title="Estadísticas de todos los eventos",
            icon="📊"
        ),
        specific_event := st.Page(
            "./pages/specific_event.py",
            title="Estadísticas de eventos específicos",
            icon="📈"
        ),
    ]
)

pg.run()
