import pandas as pd
from modelo import resolver_planificacion_turnos
from pulp import * # Asegúrate de que PuLP esté instalado: pip install pulp


# --- 1. Definición de los empleados y roles ---
empleados_test = ["Enc TM", "Enc TT", "Caj LD", "Caj LV", "Moz LD"]
roles_test = ["Encargado", "Cajero", "Mozo"]

days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
shifts = ["TM", "TT"]
turnos_test = [f"{day} {shift}" for day in days for shift in shifts]

# --- 2. Habilidades de los empleados ---
habilidades_data = {
    "Enc TM": {"Encargado": True, "Cajero": False, "Mozo": False},
    "Enc TT": {"Encargado": True, "Cajero": False, "Mozo": False},
    "Caj LD": {"Encargado": False, "Cajero": True, "Mozo": False},
    "Caj LV": {"Encargado": False, "Cajero": True, "Mozo": True},
    "Moz LD": {"Encargado": False, "Cajero": False, "Mozo": True}
}
habilidades_df_test = pd.DataFrame(habilidades_data)

# --- 3. Preferencias (disponibilidad) ---
preferencias_data = {turno: {emp: 1 for emp in empleados_test} for turno in turnos_test}

# Enc TM prefiere turno mañana (menos preferencia en TT)
for day in days:
    preferencias_data[f"{day} TT"]["Enc TM"] = 5

# Enc TT prefiere turno tarde (menos preferencia en TM)
for day in days:
    preferencias_data[f"{day} TM"]["Enc TT"] = 5

# Caj LV solo puede trabajar de lunes a viernes
for day in days[5:]:  # Sábado y Domingo
    for shift in shifts:
        preferencias_data[f"{day} {shift}"]["Caj LV"] = 0

preferencias_df_test = pd.DataFrame(preferencias_data)

# --- 4. Requisitos por rol por turno ---
requisitos_roles_data = {rol: {turno: 0 for turno in turnos_test} for rol in roles_test}
for turno in turnos_test:
    requisitos_roles_data["Encargado"][turno] = 1  # Todos los turnos
    requisitos_roles_data["Cajero"][turno] = 1      # Todos los turnos

# Mozo solo fines de semana
for day in ["Sábado", "Domingo"]:
    for shift in shifts:
        requisitos_roles_data["Mozo"][f"{day} {shift}"] = 1

requisitos_roles_df_test = pd.DataFrame(requisitos_roles_data).T

# --- 5. Turnos deseados por empleado ---
turnos_deseados_data = {
    'Empleado': empleados_test,
    'Turnos Deseados': [7, 7, 7, 4, 7]
}
turnos_deseados_df_test = pd.DataFrame(turnos_deseados_data).set_index('Empleado')

# --- 6. Total de empleados por turno ---
total_requerimientos_data = {
    turno: (3 if turno.startswith(("Sábado", "Domingo")) else 2)
    for turno in turnos_test
}
total_requerimientos_df_test = pd.DataFrame.from_dict(
    total_requerimientos_data, orient='index', columns=['Empleados Necesarios']
)


# --- Ejecutar el modelo de optimización ---
print("\n--- Ejecutando el Modelo de Optimización ---")




prob, x, y, w, z, aux, P, B, Q_val, U_val = resolver_planificacion_turnos(
    empleados_test,
    roles_test,
    habilidades_df_test,
    preferencias_df_test,
    requisitos_roles_df_test,
    turnos_deseados_df_test,
    total_requerimientos_df_test
)

dias_zimpl_indices = [i * 2 for i in range(7)]  # [0, 2, 4, 6, 8, 10, 12]

# Resolver el problema
prob.solve()

# Verificar el estado de la solución
print(f"Estado de la solución: {LpStatus[prob.status]}")
print(f"Costo Total (suma de preferencias + aux): {value(prob.objective)}")
print("-" * 30)

# --- Mostrar los resultados del plan de turnos ---
print("\n--- Plan de Turnos Asignado (x[turno][empleado]) ---")
schedule_data = {empleado: [] for empleado in empleados_test}
schedule_data['Turno'] = turnos_test

for t in turnos_test:
    for e in empleados_test:
        if x[t][e].varValue == 1:
            schedule_data[e].append("X") # Asignado
        else:
            schedule_data[e].append("") # No asignado

schedule_df = pd.DataFrame(schedule_data).set_index('Turno')
print(schedule_df)
print("-" * 30)


print("\n--- Resumen de Turnos Asignados por Empleado ---")
for e in empleados_test:
    turnos_asignados_e = sum(x[t][e].varValue for t in turnos_test)
    print(f"Empleado {e}: {int(turnos_asignados_e)} turnos asignados (Deseados: {U_val[e]})")
print("-" * 30)

print("\n--- Estado de la variable 'y' (Trabaja en el día) ---")
for m in dias_zimpl_indices:
    dia = days[m // 2]
    for e in empleados_test:
        status_y = int(y[dia][e].varValue) if y[dia][e].varValue is not None else "N/A"
        print(f"Empleado {e} - {dia}: Trabaja ({status_y})")
print("-" * 30)

print("\n--- Estado de la variable 'w' (Descansa en el día) ---")
for m in dias_zimpl_indices:
    dia = days[m // 2]
    for e in empleados_test:
        status_w = int(w[dia][e].varValue) if w[dia][e].varValue is not None else "N/A"
        print(f"Empleado {e} - {dia}: Descansa ({status_w})")
print("-" * 30)

print("\n--- Estado de la variable 'z' (Doble Turno) ---")
for m in dias_zimpl_indices:
    dia = days[m // 2]
    for e in empleados_test:
        status_z = int(z[dia][e].varValue) if z[dia][e].varValue is not None else "N/A"
        print(f"Empleado {e} - {dia}: Doble Turno ({status_z})")
print("-" * 30)