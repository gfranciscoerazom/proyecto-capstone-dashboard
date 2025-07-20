"""
Tablas: ['assistant', 'attendance', 'event', 'eventdate', 'registration', 'staffeventlink', 'user']
Tabla: assistant
  - id_number (VARCHAR(10))
  - id_number_type (ENUM)
  - phone (VARCHAR(255))
  - gender (ENUM)
  - date_of_birth (DATE)
  - accepted_terms (TINYINT)
  - user_id (INTEGER)
  - image_uuid (CHAR(32))
  Relaciones (Foreign Keys):
    - ['user_id'] -> user(['id'])
Tabla: attendance
  - event_date_id (INTEGER)
  - registration_id (INTEGER)
  - arrival_time (TIME)
  Relaciones (Foreign Keys):
    - ['event_date_id'] -> eventdate(['id'])
    - ['registration_id'] -> registration(['id'])
Tabla: event
  - name (VARCHAR(255))
  - description (TEXT)
  - location (VARCHAR(255))
  - maps_link (VARCHAR(255))
  - capacity (INTEGER)
  - capacity_type (ENUM)
  - created_at (DATETIME)
  - image_uuid (CHAR(32))
  - is_cancelled (TINYINT)
  - id (INTEGER)
  - is_published (TINYINT)
  - organizer_id (INTEGER)
  Relaciones (Foreign Keys):
    - ['organizer_id'] -> user(['id'])
Tabla: eventdate
  - day_date (DATE)
  - start_time (TIME)
  - end_time (TIME)
  - deleted (TINYINT)
  - id (INTEGER)
  - event_id (INTEGER)
  Relaciones (Foreign Keys):
    - ['event_id'] -> event(['id'])
Tabla: registration
  - id (INTEGER)
  - event_id (INTEGER)
  - assistant_id (INTEGER)
  - companion_id (INTEGER)
  - companion_type (ENUM)
  - created_at (DATETIME)
  - reaction (ENUM)
  - reaction_date (DATETIME)
  Relaciones (Foreign Keys):
    - ['event_id'] -> event(['id'])
    - ['assistant_id'] -> user(['id'])
    - ['companion_id'] -> assistant(['user_id'])
Tabla: staffeventlink
  - staff_id (INTEGER)
  - event_id (INTEGER)
  Relaciones (Foreign Keys):
    - ['staff_id'] -> user(['id'])
    - ['event_id'] -> event(['id'])
Tabla: user
  - email (VARCHAR(255))
  - first_name (VARCHAR(255))
  - last_name (VARCHAR(255))
  - id (INTEGER)
  - hashed_password (BLOB)
  - created_at (DATETIME)
  - is_active (TINYINT)
  - role (ENUM)
  Sin relaciones (Foreign Keys) (ENUM)
"""
from math import pi, ceil
import sqlalchemy
import streamlit as st
from bokeh.plotting import figure
from bokeh.models import FactorRange, ColumnDataSource, Whisker
from bokeh.transform import cumsum
from streamlit_bokeh import streamlit_bokeh  # type: ignore
import pandas as pd


def figure_config(figure: figure):
    """The basic configuration of all the figures in the app

    :param figure: The figure to configure
    :type figure: figure"""

    figure.toolbar.logo = None
    figure.toolbar.autohide = True
    figure.toolbar_location = "below"


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

    event_dates = conn.query(
        f"SELECT * FROM eventdate WHERE event_id = {event_id}"
    )

    # AttributeError: Can only use .dt accessor with datetimelike values
    # event_date_names = event_dates["day_date"].dt.strftime("%Y-%m-%d")
    event_date_names = event_dates["day_date"]

    st.sidebar.write("Fechas del evento")

    selected_event_date = st.sidebar.selectbox(
        "Selecciona una fecha del evento",
        event_date_names,
        index=None,
        placeholder="Selecciona una fecha del evento",
    )

    if selected_event_date:
        people_registered = conn.query(
            f"""
            SELECT
                r.id AS registration_id,
                r.event_id,
                r.assistant_id,
                r.companion_id,
                r.companion_type,
                r.created_at AS registration_created_at,
                r.reaction,
                r.reaction_date,
                u.created_at AS user_created_at,
                u.email,
                u.first_name,
                u.last_name,
                u.is_active,
                u.role,
                a.id_number,
                a.id_number_type,
                a.phone,
                a.gender,
                a.date_of_birth,
                att.arrival_time,
                ed.day_date
            FROM registration AS r
            JOIN user AS u ON u.id = r.companion_id
            JOIN assistant AS a ON a.user_id = u.id
            LEFT JOIN attendance AS att ON r.id = att.registration_id
            LEFT JOIN eventdate AS ed ON att.event_date_id = ed.id
            WHERE r.event_id = {event_id} AND (ed.day_date = '{selected_event_date}' OR ed.day_date IS NULL)
            """
            # f"""SELECT *
            # FROM assistant
            # JOIN registration ON assistant.user_id = registration.companion_id
            # WHERE registration.event_id = '{event_id}'"""
        )

        people_registered["age"] = pd.to_datetime("today").year - pd.to_datetime(
            people_registered["date_of_birth"]
        ).dt.year

        people_who_attended = people_registered[
            people_registered["arrival_time"].notna()
        ]

        total_people_registered = len(people_registered)
        total_people_who_attended = len(people_who_attended)
        # region Calculator
        ############################################################################
        # Calculator for the number of staff needed for the event
        #
        # To calculate the number of staff needed for the event, the following points will be taken into account:
        #     •	1 person for every 100 registered people to handle the registration.
        #     •	+10 people in case of any unforeseen event.
        #     •	1 person for every 40 registered people to handle the activities.
        #     •	In case there is any extra consideration, the organizer will have to do the calculation.
        #     •	Also, the organizer will have the option to change the default values so that the system adapts to their needs.
        ############################################################################

        show_calculator = st.toggle("Mostrar calculadora de personal")

        if show_calculator:
            st.subheader("Calculadora de personal")

            calculator_numerators, calculator_denominators = st.columns(2)

            with calculator_numerators:
                numerator_staff_by_registration = st.number_input(
                    "Número de staff por registro para manejo de la asistencia",
                    min_value=1,
                    value=1,
                    step=1
                )
                numerator_staff_by_activities = st.number_input(
                    "Número de staff por registro para el manejo de las actividades",
                    min_value=1,
                    value=1,
                    step=1
                )

            with calculator_denominators:
                denominator_staff_by_registration = st.number_input(
                    "Número de registros por staff para manejo de la asistencia",
                    min_value=1,
                    value=100,
                    step=1
                )
                denominator_staff_by_activities = st.number_input(
                    "Número de registros por staff para manejo de las actividades",
                    min_value=1,
                    value=40,
                    step=1
                )

            staff_for_unforeseen = st.number_input(
                "Número de staff para imprevistos",
                min_value=0,
                value=10,
                step=1
            )

            additional_staff = st.number_input(
                "Número de staff adicional",
                min_value=0,
                value=0,
                step=1
            )

            expected_registrations = st.number_input(
                "Número de gente registrada",
                min_value=1,
                value=total_people_registered,
                step=1
            )

            staff_needed = (
                ceil((expected_registrations / denominator_staff_by_registration) * numerator_staff_by_registration) + staff_for_unforeseen +
                ceil((expected_registrations / denominator_staff_by_activities) *
                     numerator_staff_by_activities) + additional_staff
            )

            st.badge(
                f"El número total de staff recomendado para el evento es de **{staff_needed:.0f}** personas"
            )

        # endregion
        # region Show data
        ############################################################################
        # Section to show the data of the people registered for the event

        # This section shows the data of the people registered for the event or the people who attended the event
        # depending on the checkbox selected by the user
        ############################################################################

        show_data = st.toggle("Mostrar datos de los asistentes")

        if show_data:
            data_to_show = st.radio(
                "Selecciona el tipo de datos que quieres ver",
                ("Gente registrada", "Gente que asistió"),
                index=0,
                horizontal=True,
            )

            if data_to_show == "Gente registrada":
                st.subheader("Datos de los registrados")
                st.dataframe(people_registered)
            elif data_to_show == "Gente que asistió":
                st.subheader("Datos de los asistentes")
                st.dataframe(people_who_attended)

        # endregion
        # region Registered vs Attended
        ############################################################################
        # Section to analyze the people registered for the event vs the people who attended the event
        #
        # This section answers the following questions:
        #     •	How many people registered for the event?
        #     •	How many people attended the event?
        #     •	How many people did not attend the event?
        #     •	What is the percentage of people who attended the event vs the people who registered for the event?
        ############################################################################

        st.subheader("Asistencia vs Registro")

        # Pie chart to compare the number of people registered for the event vs the number of people who attended the event
        attendance_pie_chart_data = pd.Series({
            "Asistieron": total_people_who_attended,
            "No asistieron": total_people_registered - total_people_who_attended,
        }).reset_index(name="value").rename(columns={
            "index": "Asistencia"
        })

        attendance_pie_chart_data['angle'] = attendance_pie_chart_data.value / \
            attendance_pie_chart_data.value.sum() * 2 * pi
        attendance_pie_chart_data['percentage'] = attendance_pie_chart_data.value / \
            attendance_pie_chart_data.value.sum() * 100
        attendance_pie_chart_data['color'] = ["green", "red"]

        assistant_pie_chart = figure(
            title="Gente registrada vs gente que asistió",
            tools="hover,tap,save,reset,help",
            tooltips="@Asistencia: @value (@percentage{0.2f}%)",
            x_range=(-0.5, 1.0),
        )

        assistant_pie_chart.wedge(
            x=0,
            y=1,
            radius=0.4,
            start_angle=cumsum("angle", include_zero=True),
            end_angle=cumsum("angle"),
            line_color=None,
            fill_color="color",
            legend_field="Asistencia",
            source=attendance_pie_chart_data,
        )

        figure_config(assistant_pie_chart)
        assistant_pie_chart.axis.axis_label = None
        assistant_pie_chart.axis.visible = False
        assistant_pie_chart.grid.grid_line_color = None

        # Display all the statistics
        total_registrations_col, total_attendance_col = st.columns(2)

        with total_registrations_col:
            streamlit_bokeh(assistant_pie_chart)

        with total_attendance_col:
            st.metric(
                label="Total de Personas que Asistieron al Evento",
                value=total_people_who_attended,
                border=True,
            )

            st.metric(
                label="Total de Personas Registradas al Evento",
                value=total_people_registered,
                border=True,
            )

            try:
                st.badge(
                    f"Por lo tanto, el porcentaje de asistencia es del **{total_people_who_attended / total_people_registered * 100:.2f}%**"
                )
            except ZeroDivisionError:
                st.badge(
                    "Aún no hay gente inscrita en el evento."
                )

        st.divider()
        # endregion
        # region Age of the assistants
        ############################################################################
        # Section to analyze the age of the assistants of the event
        #
        # This section answers the following questions:
        #     •	What is the age distribution of the assistants of the event?
        #     •	What is the average age of the assistants of the event?
        #     •	What is the median age of the assistants of the event?
        #     •	What is the age of the youngest assistant of the event?
        #     •	What is the age of the oldest assistant of the event?
        ############################################################################

        st.subheader("Edad de los asistentes")

        # Bar chart to show the age distribution of the assistants
        age_range = st.slider(
            "Selecciona el rango de edad que quieres analizar",
            value=(0, 150),
            step=1,
        )

        age_counts = people_who_attended["age"].value_counts()
        age_counts = age_counts[age_counts.index >= age_range[0]]
        age_counts = age_counts[age_counts.index <= age_range[1]]
        age_counts = age_counts.sort_index()
        age_counts = age_counts.reset_index()
        age_counts.columns = ["Edad", "Cantidad"]
        age_counts["Edad"] = age_counts["Edad"].astype(str)
        age_counts["Cantidad"] = age_counts["Cantidad"].astype(int)
        age_counts["color"] = "blue"

        age_bar_chart = figure(
            title="Distribución de Edad de los que asistieron al evento",
            x_axis_label="Edad",
            y_axis_label="Cantidad",
            x_range=age_counts["Edad"].tolist(),
            height=350,
        )

        age_bar_chart.vbar(
            x="Edad",
            top="Cantidad",
            width=0.9,
            color="color",
            source=age_counts,
        )

        figure_config(age_bar_chart)
        age_bar_chart.xgrid.grid_line_color = None
        age_bar_chart.xaxis.major_label_orientation = "vertical"

        # Boxplot to show the age distribution of the assistants
        ages = people_who_attended["age"]

        # Calcular estadísticas necesarias para el boxplot
        q1 = ages.quantile(0.25)  # Primer cuartil
        q2 = ages.median()        # Mediana
        q3 = ages.quantile(0.75)  # Tercer cuartil
        iqr = q3 - q1             # Rango intercuartílico (IQR)
        lower_bound = max(ages.min(), q1 - 1.5 * iqr)  # Límite inferior
        upper_bound = min(ages.max(), q3 + 1.5 * iqr)  # Límite superior

        # Crear un DataFrame con los datos para el boxplot
        boxplot_data = pd.DataFrame({
            "category": ["Edades"],
            "q1": [q1],
            "q2": [q2],
            "q3": [q3],
            "lower": [lower_bound],
            "upper": [upper_bound]
        })

        # Fuente de datos para Bokeh
        source = ColumnDataSource(boxplot_data)

        # Crear la figura del boxplot
        boxplot = figure(
            title="Distribución de Edades de los Asistentes",
            y_range=["Edades"],  # Cambiar a y_range para un gráfico horizontal
            x_axis_label="Edad",
            x_range=age_range,
            height=150
        )

        # Dibujar las cajas del boxplot (horizontal)
        boxplot.hbar(y="category", height=0.4, left="q2", right="q3",
                     source=source, color="blue", line_color="black")
        boxplot.hbar(y="category", height=0.4, left="q1", right="q2",
                     source=source, color="blue", line_color="black")

        # Dibujar los bigotes (whiskers)
        whisker = Whisker(base="category", upper="upper",
                          lower="lower", dimension="width", source=source)
        whisker.upper_head.size = whisker.lower_head.size = 10
        boxplot.add_layout(whisker)

        # Opciones de estilo
        figure_config(boxplot)
        boxplot.ygrid.grid_line_color = None
        boxplot.yaxis.major_label_orientation = "horizontal"

        # Display the statistics of the age of the assistants
        age_statistics_col1, age_statistics_col2 = st.columns(2)

        with age_statistics_col1:
            streamlit_bokeh(age_bar_chart)

        with age_statistics_col2:
            st.metric(
                label="Edad promedio de los asistentes",
                value=people_who_attended["age"].mean(),
                border=True,
            )
            st.metric(
                label="Edad mediana de los asistentes",
                value=people_who_attended["age"].median(),
                border=True,
            )
            st.metric(
                label="Edad de la persona más joven",
                value=people_who_attended["age"].min(),
                border=True,
            )
            st.metric(
                label="Edad de la persona más vieja",
                value=people_who_attended["age"].max(),
                border=True,
            )

        streamlit_bokeh(boxplot)

        st.divider()
        # endregion
        # region Gender of the assistants
        ############################################################################
        # Section to analyze the gender of the assistants of the event
        #
        # This section answers the following questions:
        #     •	How many males, females, and others attended the event?
        #     •	What is the percentage of each gender in relation to the total attendees?
        ############################################################################

        st.subheader("Género de los asistentes")

        # Bar chart to visualize the number of attendees by gender
        gender_counts = people_registered['gender'].value_counts()
        gender_counts = (
            gender_counts.get("MALE", 0),
            gender_counts.get("FEMALE", 0),
            gender_counts.get("OTHER", 0),
        )

        gender_range = ("HOMBRE", "MUJER", "OTRO")
        gender_colors = ("blue", "pink", "gray")
        gender_source = ColumnDataSource(
            data=dict(
                range=gender_range,
                counts=gender_counts,
                colors=gender_colors,
            )
        )

        gender_bar_chart = figure(
            title="Género de los asistentes",
            x_axis_label="Cantidad de asistentes",
            y_axis_label="Género",
            x_range=FactorRange(factors=gender_range),
        )

        gender_bar_chart.vbar(
            source=gender_source,
            x="range",
            top="counts",
            width=0.9,
            color="colors",
            legend_field="range",
        )

        gender_bar_chart.xgrid.grid_line_color = None
        gender_bar_chart.toolbar.logo = None
        gender_bar_chart.add_tools("tap")

        # Display the statistics of gender attendance
        streamlit_bokeh(gender_bar_chart)

        gender_statistics_col1, gender_statistics_col2, gender_statistics_col3 = st.columns(
            3)

        with gender_statistics_col1:
            try:
                st.metric(
                    label="Cantidad de hombres",
                    value=f"{gender_counts[0]} ({(gender_counts[0] / sum(gender_counts) * 100):.2f}%)",
                    border=True,
                )
            except ZeroDivisionError:
                st.metric(
                    label="Cantidad de hombres",
                    value="0 (0.00%)",
                    border=True,
                )

        with gender_statistics_col2:
            try:
                st.metric(
                    label="Cantidad de mujeres",
                    value=f"{gender_counts[1]} ({(gender_counts[1] / sum(gender_counts) * 100):.2f}%)",
                    border=True,
                )
            except ZeroDivisionError:
                st.metric(
                    label="Cantidad de mujeres",
                    value="0 (0.00%)",
                    border=True,
                )

        with gender_statistics_col3:
            try:
                st.metric(
                    label="Cantidad de otros",
                    value=f"{gender_counts[2]} ({(gender_counts[2] / sum(gender_counts) * 100):.2f}%)",
                    border=True,
                )
            except ZeroDivisionError:
                st.metric(
                    label="Cantidad de otros",
                    value="0 (0.00%)",
                    border=True,
                )

        st.divider()
        # endregion
        # region People who registered to previous events
        ############################################################################
        # Section to analyze the people who registered for previous events
        #
        # This section answers the following questions:
        #     •	How many people registered for previous events?
        ############################################################################
        id_all_assistants = people_registered["companion_id"]
        try:
            registrations_for_other_events = conn.query(
                f"""SELECT * FROM registration WHERE companion_id IN ({','.join(map(str, id_all_assistants))}) AND event_id != '{event_id}'"""
            )
        except sqlalchemy.exc.ProgrammingError:
            registrations_for_other_events = pd.DataFrame()

        try:
            count_people_registered_previous_events = len(
                registrations_for_other_events["companion_id"].unique()
            )
        except KeyError:
            count_people_registered_previous_events = 0

        st.metric(
            label="Cantidad de personas registradas en eventos anteriores",
            value=count_people_registered_previous_events,
            border=True,
        )
        st.divider()
        # endregion
        # region Assistance hour
        ############################################################################
        # Section to analyze the attendance hour of the assistants of the event
        #
        # This section answers the following questions:
        #     •	What is the attendance hour of the assistants of the event?
        #     •	What is the average attendance hour of the assistants of the event?
        #     •	What is the most common attendance hour of the assistants of the event?
        #     •	What is the least common attendance hour of the assistants of the event?
        ############################################################################

        st.subheader("Hora de asistencia")

        hour_range = st.slider(
            "Selecciona el rango de hora que quieres analizar",
            min_value=0,
            max_value=24,
            value=(0, 24),
        )

        # Bar chart to show the attendance hour of the assistants
        try:
            attendance_hour_counts = people_registered["arrival_time"].dt.components.hours.value_counts(
            )
        except AttributeError:
            attendance_hour_counts = pd.Series(dtype=int)

        attendance_hour_counts = attendance_hour_counts[
            attendance_hour_counts.index >= hour_range[0]]
        attendance_hour_counts = attendance_hour_counts[
            attendance_hour_counts.index <= hour_range[1]]
        attendance_hour_counts = attendance_hour_counts.sort_index()
        attendance_hour_counts = attendance_hour_counts.reset_index()
        attendance_hour_counts.columns = ["Hora", "Cantidad"]
        attendance_hour_counts["Hora"] = attendance_hour_counts["Hora"].astype(
            str)
        attendance_hour_counts["Cantidad"] = attendance_hour_counts["Cantidad"].astype(
            int)
        attendance_hour_counts["color"] = "blue"

        hour_bar_chart = figure(
            title="Distribución de Hora de Asistencia de los asistentes",
            x_axis_label="Hora",
            y_axis_label="Cantidad",
            x_range=attendance_hour_counts["Hora"].tolist(),
            height=350,
        )

        hour_bar_chart.vbar(
            x="Hora",
            top="Cantidad",
            width=0.9,
            color="color",
            source=attendance_hour_counts,
        )

        figure_config(hour_bar_chart)
        hour_bar_chart.xgrid.grid_line_color = None
        hour_bar_chart.xaxis.major_label_orientation = "vertical"
        hour_bar_chart.y_range.start = 0

        # Display the statistics of the attendance hour of the assistants
        hour_statistics_col1, hour_statistics_col2 = st.columns(2)

        with hour_statistics_col1:
            streamlit_bokeh(hour_bar_chart)

        with hour_statistics_col2:
            try:
                st.metric(
                    label="Hora promedio de asistencia",
                    value=people_registered["arrival_time"].dt.components.hours.mean(
                    ),
                    border=True,
                )
            except AttributeError:
                st.metric(
                    label="Hora promedio de asistencia",
                    value="No disponible",
                    border=True,
                )

            try:
                st.metric(
                    label="Hora más concurrida de asistencia",
                    value=people_registered["arrival_time"].dt.components.hours.mode()[
                        0],
                    border=True,
                )
            except AttributeError:
                st.metric(
                    label="Hora más concurrida de asistencia",
                    value="No disponible",
                    border=True,
                )

        st.divider()
        # endregion
        ############################################################################
        # Section to analyze reactions of the assistants of the event
        ############################################################################

        st.subheader("Likes vs Dislikes vs Sin reacción")

        # Total number of registrations, this only includes LIKE, DISLIKE because NO_REACTION means that the user has not reacted yet
        st.metric(
            label="Total de reacciones",
            value=people_registered[
                people_registered["reaction"].isin(("LIKE", "DISLIKE"))
            ].shape[0],
        )

        reaction_counts = people_registered["reaction"].value_counts()
        reaction_counts = (
            reaction_counts.get("LIKE", 0),
            reaction_counts.get("DISLIKE", 0),
            reaction_counts.get("NO_REACTION", 0),
        )
        reactions_range = ("LIKE", "DISLIKE", "SIN REACCIÓN")
        reaction_colors = ("green", "red", "gray")
        reaction_source = ColumnDataSource(
            data=dict(
                range=reactions_range,
                counts=reaction_counts,
                colors=reaction_colors,
            )
        )

        reaction_bar_chart = figure(
            title="Reacciones de los usuarios",
            x_axis_label="Reacciones",
            y_axis_label="Cantidad de usuarios",
            x_range=FactorRange(factors=reactions_range),
        )

        reaction_bar_chart.vbar(
            source=reaction_source,
            x="range",
            top="counts",
            width=0.9,
            color="colors",
            legend_field="range",
        )

        reaction_bar_chart.xgrid.grid_line_color = None
        reaction_bar_chart.toolbar.logo = None
        reaction_bar_chart.add_tools("tap")

        streamlit_bokeh(reaction_bar_chart)

        st.divider()
