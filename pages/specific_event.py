import streamlit as st
from bokeh.plotting import figure
from streamlit_bokeh import streamlit_bokeh  # type: ignore

st.title("Estadísticas de eventos específicos")

st.sidebar.title("Estadísticas de eventos específicos 📈")

conn = st.connection("sql")

events = conn.query("SELECT * FROM event")

event_names = events["name"]

selected_event = st.sidebar.selectbox(
    "Selecciona un evento",
    event_names,
    index=None,
    placeholder="Selecciona un evento",
)


if selected_event:
    event_id = events[events["name"] == selected_event]["id"].values[0]

    st.subheader("Likes vs Dislikes vs Sin reacción")

    registrations = conn.query(
        f"SELECT * FROM registration WHERE event_id = '{event_id}'"
    )

    likes = len(
        registrations[registrations["reaction"] == "LIKE"]
    )
    dislikes = len(
        registrations[registrations["reaction"] == "DISLIKE"]
    )
    no_reaction = len(
        registrations[registrations["reaction"] == "NO_REACTION"]
    )

    p = figure(
        title="Reacciones de los usuarios",
        x_axis_label="Reacciones",
        y_axis_label="Cantidad de usuarios",
        x_range=["LIKE", "DISLIKE", "SIN REACCIÓN"],
    )

    p.vbar(
        x=["LIKE", "DISLIKE", "SIN REACCIÓN"],
        top=[likes, dislikes, no_reaction],
        width=0.9
    )

    streamlit_bokeh(p)

    st.dataframe(registrations)
