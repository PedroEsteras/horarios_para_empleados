import streamlit as st
import pandas as pd
from pulp import * # Se ha descomentado la importación de PuLP
from modelo import resolver_planificacion_turnos # Asegúrate de que modelo.py está en el mismo directorio
from PIL import Image



st.set_page_config(layout="wide")

imagen = Image.open("logo_grande.png")

col1, col2, col3 = st.columns([1, 1, 1])  # la del medio es más ancha
with col1:
    st.image(imagen, width=200)

st.markdown(
'<a href="https://www.bonanzasol.com.ar" target="_blank">www.bonanzasol.com.ar</a>',
unsafe_allow_html=True
)

st.markdown("Es mejor y mas comodo usar el sistema desde la computadora.")

st.title("Sistema de Planificación de Turnos para tu Comercio")
st.markdown("""
El sistema esta destinado a comercios que trabajan todos los dias de la semana, con dos turnos por dia.


Esta aplicación te permite configurar los datos iniciales para la planificación de turnos.
Luego, podrás ejecutar el **modelo de optimización** para generar una propuesta de horarios.

**Pasos:**\n
0. **Cantidad minima de feriados y cantidad maxima de turnos dobles por empleado**: Define las restricciones de feriados y turnos dobles.
1.  **Nombres de los Empleados**: Define tu personal.
2.  **Tipos de Roles**: Lista las funciones en tu comercio.
3.  **Asignación de Roles por Empleado**: Indica qué roles puede desempeñar cada empleado.
4.  **Horarios Disponibles de Empleados**: Registra las preferencias de cada empleado por turno.
5.  **Requisitos de Roles por Turno**: Especifica la cantidad de empleados por rol en cada turno.
6.  **Turnos Deseados por Empleado**: Define cuántos turnos debe hacer cada empleado.
7.  **Requisitos Totales de Empleados por Turno**: Indica el personal total necesario en cada turno.\n
""")



st.header("0. Cantidad de Feriados y Turnos Dobles")
st.markdown("Por favor, ingresa el número de minimo de feriados y maximo de doble turno por empleado.")


feriados = st.number_input(
    "Cantidad mínima de feriados por empleado",
    min_value=0,
    value=1,
    step=1,
    help="Define la cantidad mínima de días feriados que debe tener cada empleado."
)

dobles = st.number_input(
    "Cantidad máxima de turnos dobles por empleado",
    min_value=0,
    value=1,
    step=1,
    help="Define la cantidad máxima de turnos dobles permitidos para cada empleado."
)

st.header("1. Nombres de los Empleados")
st.markdown("Por favor, ingresa el número de empleados y sus nombres.")

num_employees = st.number_input(
    "Número de Empleados",
    min_value=1,
    value=2,
    step=1,
    help="Define cuántos empleados quieres ingresar."
)




employee_names = []
for i in range(int(num_employees)):
    name = st.text_input(f"Nombre del Empleado {i+1}", key=f"employee_name_{i}")
    if name:
        employee_names.append(name)

if not employee_names:
    st.warning("Por favor, ingresa al menos un nombre de empleado para continuar.")

st.session_state['employee_names'] = employee_names # Guardar en session_state


st.header("2. Tipos de Roles en tu Comercio")
st.markdown("Lista los roles disponibles, uno por línea.")

roles_raw = st.text_area(
    "Lista de Roles (uno por línea)",
    "Encargado\nCajero\nMozo",
    height=150,
    help="Escribe cada rol en una nueva línea (ej: Cajero, Repositor)."
)

roles = [role.strip() for role in roles_raw.split('\n') if role.strip()]
roles = sorted(list(set(roles)))

if not roles:
    st.warning("Por favor, ingresa al menos un rol para continuar.")

st.session_state['roles'] = roles # Guardar en session_state


st.header("3. Asignación de Roles por Empleado")
st.markdown("Para cada empleado, marca los roles que puede desempeñar (matriz de habilidades).")

if employee_names and roles:
    assignment_data = {}
    for employee in employee_names:
        assignment_data[employee] = {role: False for role in roles}
    assignment_df = pd.DataFrame(assignment_data).T

    column_config_assign = {role: st.column_config.CheckboxColumn(role, help=f"¿Puede este empleado desempeñar el rol de {role}?", default=False) for role in roles}

    edited_assignment_df = st.data_editor(
        assignment_df,
        column_config=column_config_assign,
        hide_index=False,
        use_container_width=True,
        height=min(300, (len(employee_names) + 1) * 35)
    )
    st.session_state['edited_assignment_df'] = edited_assignment_df
else:
    st.info("Ingresa los nombres de los empleados y los roles para ver la tabla de asignación.")


st.header("4. Horarios Disponibles de Empleados")
st.markdown("Para cada empleado, ingresa su preferencia para cada horario (0 = No disponible, 1 = Le gusta mucho, 5 = Lo odia).")

days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
shifts = ["TM", "TT"]
time_slots = [f"{day} {shift}" for day in days for shift in shifts]

if employee_names:
    availability_data = {}
    for slot in time_slots:
        availability_data[slot] = {employee: 0 for employee in employee_names}
    availability_df = pd.DataFrame(availability_data)

    availability_column_config = {}
    for employee in employee_names:
        availability_column_config[employee] = st.column_config.NumberColumn(
            employee,
            min_value=0, max_value=5, step=1, format="%d",
            help=f"Preferencia de {employee} para este horario (0=No disponible, 1=Le gusta mucho, 5=Lo odia)"
        )

    edited_availability_df = st.data_editor(
        availability_df,
        column_config=availability_column_config,
        hide_index=False,
        use_container_width=True,
        # Eliminado el parámetro height para que la tabla se expanda completamente
    )
    st.session_state['edited_availability_df'] = edited_availability_df
else:
    st.info("Ingresa los nombres de los empleados para configurar los horarios disponibles.")


st.header("5. Requisitos de Roles por Turno")
st.markdown("Para cada turno, ingresa la cantidad de empleados necesarios para cada rol.")

if roles and time_slots:
    role_requirements_data = {}
    for role in roles:
        role_requirements_data[role] = {slot: 0 for slot in time_slots}
    role_requirements_df = pd.DataFrame(role_requirements_data)

    role_requirements_column_config = {}
    for slot in time_slots:
        role_requirements_column_config[slot] = st.column_config.NumberColumn(
            slot, min_value=0, step=1, format="%d",
            help=f"Cantidad necesaria del rol en el turno de {slot}"
        )

    edited_role_requirements_df = st.data_editor(
        role_requirements_df,
        column_config=role_requirements_column_config,
        hide_index=False,
        use_container_width=True,
    )
    st.session_state['edited_role_requirements_df'] = edited_role_requirements_df
else:
    st.info("Ingresa los roles y asegúrate de que los horarios estén definidos para configurar los requisitos por turno.")


st.header("6. Turnos Deseados por Empleado")
st.markdown("Para cada empleado, especifica el número de turnos que debe realizar a la semana.")

if employee_names:
    desired_shifts_data = {
        'Empleado': employee_names,
        'Turnos Deseados': [1] * len(employee_names) # Valor por defecto
    }
    desired_shifts_df = pd.DataFrame(desired_shifts_data).set_index('Empleado')

    desired_shifts_column_config = {
        'Turnos Deseados': st.column_config.NumberColumn(
            'Turnos Deseados', min_value=0, step=1, format="%d",
            help="Número total de turnos que el empleado debe realizar."
        )
    }

    edited_desired_shifts_df = st.data_editor(
        desired_shifts_df,
        column_config=desired_shifts_column_config,
        hide_index=False,
        use_container_width=True,
    )
    st.session_state['edited_desired_shifts_df'] = edited_desired_shifts_df
else:
    st.info("Ingresa los nombres de los empleados para especificar sus turnos deseados.")


st.header("7. Requisitos Totales de Empleados por Turno")
st.markdown("Para cada turno, ingresa la cantidad total de empleados necesarios.")

if time_slots:
    total_requirements_data = {
        'Turno': time_slots,
        'Empleados Necesarios': [1] * len(time_slots) # Valor por defecto
    }
    total_requirements_df = pd.DataFrame(total_requirements_data).set_index('Turno')

    total_requirements_column_config = {
        'Empleados Necesarios': st.column_config.NumberColumn(
            'Empleados Necesarios', min_value=0, step=1, format="%d",
            help="Número total de empleados requeridos en este turno."
        )
    }

    edited_total_requirements_df = st.data_editor(
        total_requirements_df,
        column_config=total_requirements_column_config,
        hide_index=False,
        use_container_width=True,
    )
    st.session_state['edited_total_requirements_df'] = edited_total_requirements_df
else:
    st.info("Asegúrate de que los horarios estén definidos para configurar los requisitos totales por turno.")


st.header("8. Ejecutar la Planificación de Turnos")
st.markdown("Una vez que hayas configurado todos los datos, haz clic en el botón para generar la planificación optimizada.")

if st.button("Ejecutar Planificación"):
    # Comprobar que los datos esenciales estén presentes antes de ejecutar el modelo
    if (not st.session_state.get('employee_names') or
        not st.session_state.get('roles') or
        st.session_state.get('edited_assignment_df') is None or
        st.session_state.get('edited_availability_df') is None or
        st.session_state.get('edited_role_requirements_df') is None or
        st.session_state.get('edited_desired_shifts_df') is None or
        st.session_state.get('edited_total_requirements_df') is None):
        st.error("Por favor, completa todas las secciones de entrada de datos antes de ejecutar la planificación.")
    else:
        with st.spinner('Ejecutando el modelo de optimización... esto puede tardar un momento.'):
            try:
                # Recuperar los datos de session_state
                empleados = st.session_state['employee_names']
                roles = st.session_state['roles']
                habilidades_df = st.session_state['edited_assignment_df'].T
                preferencias_df = st.session_state['edited_availability_df']
                requisitos_roles_df = st.session_state['edited_role_requirements_df'].T
                turnos_deseados_df = st.session_state['edited_desired_shifts_df']
                total_requerimientos_df = st.session_state['edited_total_requirements_df']

                # Ajustar habilidades_df para que el índice sea el empleado y las columnas los roles (como espera modelo.py)
                # El data_editor devuelve un DataFrame con el índice que se le pasó (empleados) y columnas (roles)
                # La función resolver_planificacion_turnos espera habilidades_df con empleados como índice y roles como columnas.
                # Ya que en la app se usa .T al inicializar assignment_df, el edited_assignment_df ya viene traspuesto
                # entonces no necesitamos transponerlo de nuevo aquí, simplemente se pasa como está.

                # Llamar al modelo de optimización
                # Asegúrate de que todas las variables que retorna el modelo sean capturadas
                prob, x, y, w, z, aux, P, B, Q_val, U_val = resolver_planificacion_turnos(
                    empleados,
                    roles,
                    habilidades_df,
                    preferencias_df,
                    requisitos_roles_df,
                    turnos_deseados_df,
                    total_requerimientos_df,
                    feriados,
                    dobles
                )

                # Resolver el problema
                prob.solve()

                # Mostrar el estado de la solución
                st.subheader("Resultados de la Optimización")
                st.write(f"**Estado de la solución:** `{LpStatus[prob.status]}`")

                if LpStatus[prob.status] == "Optimal":
                    st.success("¡Planificación generada con éxito!")
                    st.write(f"**Costo Total (suma de preferencias + balanceo):** `{value(prob.objective):.2f}`")
                    st.write(f"**Mínimo de turnos asignados a cualquier empleado (variable 'aux'):** `{value(aux):.0f}`")

                    # --- Visualización del Plan de Turnos Asignado ---
                    st.markdown("### Plan de Turnos Asignado")

                    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                    shifts = ["TM", "TT"] # Turno Mañana, Turno Tarde
                    turnos = [f"{day} {shift}" for day in days for shift in shifts]
                    schedule_data_display = {'Turno': turnos} # 'turnos' debe ser definido o importado
                    
                    # days y shifts son globales en app.py, por lo que turnos también lo es.
                    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                    shifts = ["TM", "TT"]
                    turnos = [f"{day} {shift}" for day in days for shift in shifts]

                    schedule_data_display = {'Turno': turnos}
                    for empleado in empleados:
                        schedule_data_display[empleado] = []

                    for t in turnos:
                        for e in empleados:
                            if x[t][e].varValue == 1:
                                schedule_data_display[e].append("X") # Asignado
                            else:
                                schedule_data_display[e].append("") # No asignado

                    schedule_df_display = pd.DataFrame(schedule_data_display).set_index('Turno')
                    st.dataframe(schedule_df_display)

                    # --- Resumen de Turnos Asignados por Empleado ---
                    st.markdown("### Resumen de Turnos Asignados por Empleado")
                    assigned_shifts_summary = []
                    for e in empleados:
                        turnos_asignados_e = sum(x[t][e].varValue for t in turnos)
                        assigned_shifts_summary.append({
                            "Empleado": e,
                            "Turnos Asignados": int(turnos_asignados_e),
                            "Turnos Deseados": U_val[e]
                        })
                    st.dataframe(pd.DataFrame(assigned_shifts_summary).set_index("Empleado"))

                elif LpStatus[prob.status] == "Infeasible":
                    st.error("El modelo de optimización encontró que no es posible generar una planificación que cumpla con todas las restricciones dadas. Por favor, revisa tus requisitos de entrada (disponibilidades, habilidades, turnos deseados, requisitos de roles y totales) e intenta relajar algunas.")
                else:
                    st.warning(f"El modelo terminó con un estado: {LpStatus[prob.status]}. Esto podría indicar un problema. Intenta revisar tus datos.")

            except Exception as e:
                st.error(f"Ocurrió un error al ejecutar el modelo: {e}. Por favor, verifica tus datos de entrada y el archivo `modelo.py`.")




st.markdown("""
<div style="background-color:#f0f2f6; padding:15px; border-radius:10px; text-align:center;">
    Si tienes alguna duda sobre el uso, encontraste un error o quieres hacer un comentario,
    no dudes en contactarnos: <a href="mailto:info@bonanzasol.com.ar">info@bonanzasol.com.ar</a>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
# st.subheader("Resumen de la Configuración:")
# st.markdown("Aquí puedes ver el contenido de todas las tablas que has configurado:")

# # --- Sección para imprimir tablas en la consola ---
# st.markdown("### Ver Tablas en la Consola (para depuración)")
# st.markdown("Haz clic en el botón para imprimir los datos de todas las tablas en la consola de tu terminal.")

# if st.button("Imprimir Tablas en Consola"):
#     if 'employee_names' in st.session_state:
#         print("\n--- Empleados Registrados ---")
#         print(st.session_state['employee_names'])

#     if 'roles' in st.session_state:
#         print("\n--- Roles Registrados ---")
#         print(st.session_state['roles'])

#     if 'edited_assignment_df' in st.session_state and not st.session_state['edited_assignment_df'].empty:
#         print("\n--- Matriz de Habilidades (Asignación de Roles) ---")
#         print(st.session_state['edited_assignment_df'].T)

#     if 'edited_availability_df' in st.session_state and not st.session_state['edited_availability_df'].empty:
#         print("\n--- Preferencias de Horarios ---")
#         print(st.session_state['edited_availability_df'])

#     if 'edited_role_requirements_df' in st.session_state and not st.session_state['edited_role_requirements_df'].empty:
#         print("\n--- Requisitos de Roles por Turno ---")
#         print(st.session_state['edited_role_requirements_df'].T)

#     if 'edited_desired_shifts_df' in st.session_state and not st.session_state['edited_desired_shifts_df'].empty:
#         print("\n--- Turnos Deseados por Empleado ---")
#         print(st.session_state['edited_desired_shifts_df'])

#     if 'edited_total_requirements_df' in st.session_state and not st.session_state['edited_total_requirements_df'].empty:
#         print("\n--- Requisitos Totales de Empleados por Turno ---")
#         print(st.session_state['edited_total_requirements_df'])
#     st.success("Tablas impresas en la consola. ¡Revisa tu terminal!")
# # --- Fin de la impresión de tablas en la consola ---


# # Visualización de las tablas en la interfaz de usuario de Streamlit
# st.markdown("### Empleados Registrados:")
# if 'employee_names' in st.session_state and st.session_state['employee_names']:
#     st.dataframe(pd.DataFrame(st.session_state['employee_names'], columns=["Nombre del Empleado"]))
# else:
#     st.info("Por favor, ingresa los nombres de los empleados en la Sección 1.")

# st.markdown("### Roles Registrados:")
# if 'roles' in st.session_state and st.session_state['roles']:
#     st.dataframe(pd.DataFrame(st.session_state['roles'], columns=["Nombre del Rol"]))
# else:
#     st.info("Por favor, ingresa los roles en la Sección 2.")

# st.markdown("### Matriz de Habilidades (Asignación de Roles):")
# if 'edited_assignment_df' in st.session_state and not st.session_state['edited_assignment_df'].empty:
#     st.dataframe(st.session_state['edited_assignment_df'])
# else:
#     st.info("Completa la sección de asignación de roles (Sección 3) para ver la matriz de habilidades.")

# st.markdown("### Preferencias de Horarios:")
# if 'edited_availability_df' in st.session_state and not st.session_state['edited_availability_df'].empty:
#     st.dataframe(st.session_state['edited_availability_df'])
# else:
#     st.info("Completa la sección de horarios disponibles (Sección 4) para ver las preferencias.")

# st.markdown("### Requisitos de Roles por Turno:")
# if 'edited_role_requirements_df' in st.session_state and not st.session_state['edited_role_requirements_df'].empty:
#     st.dataframe(st.session_state['edited_role_requirements_df'])
# else:
#     st.info("Completa la sección de requisitos de roles por turno (Sección 5) para ver la matriz de requisitos.")

# st.markdown("### Turnos Deseados por Empleado:")
# if 'edited_desired_shifts_df' in st.session_state and not st.session_state['edited_desired_shifts_df'].empty:
#     st.dataframe(st.session_state['edited_desired_shifts_df'])
# else:
#     st.info("Completa la sección de turnos deseados por empleado (Sección 6) para ver esta tabla.")

# st.markdown("### Requisitos Totales de Empleados por Turno:")
# if 'edited_total_requirements_df' in st.session_state and not st.session_state['edited_total_requirements_df'].empty:
#     st.dataframe(st.session_state['edited_total_requirements_df'])
# else:
#     st.info("Completa la sección de requisitos totales de empleados por turno (Sección 7) para ver esta tabla.")


# st.markdown("---")
# st.info("Guarda este código como un archivo `.py` y ejecútalo con `streamlit run tu_archivo.py`.")

