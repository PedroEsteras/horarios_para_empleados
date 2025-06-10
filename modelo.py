import pandas as pd
from pulp import *



def resolver_planificacion_turnos(
    empleados: list, # Nombres de los empleados (Ej: ["Juan", "Maria"])
    roles: list,     # Nombres de los roles (Ej: ["Cajero", "Mozo"])
    habilidades_df: pd.DataFrame,          # Datos de la Sección 3 (Asignación de Roles por Empleado)
    preferencias_df: pd.DataFrame,         # Datos de la Sección 4 (Horarios Disponibles de Empleados)
    requisitos_roles_df: pd.DataFrame,     # Datos de la Sección 5 (Requisitos de Roles por Turno)
    turnos_deseados_df: pd.DataFrame,      # Datos de la Sección 6 (Turnos Deseados por Empleado)
    total_requerimientos_df: pd.DataFrame,  # Datos de la Sección 7 (Requisitos Totales de Empleados por Turno)
    cantidad_de_francos: int = 1, # Cantidad de días de descanso por empleado (default: 1)
    cantidad_de_dobles: int = 1   # Cantidad de días con doble turno por empleado (default: 1)
):
    """
    Construye y resuelve el modelo de planificación de turnos utilizando PuLP.

    Args:
        empleados (list): Lista de nombres de empleados.
        roles (list): Lista de nombres de roles.
        habilidades_df (pd.DataFrame): DataFrame con habilidades de los empleados para los roles.
        preferencias_df (pd.DataFrame): DataFrame con preferencias de turnos por empleado.
        requisitos_roles_df (pd.DataFrame): DataFrame con la cantidad de roles necesarios por turno.
        turnos_deseados_df (pd.DataFrame): DataFrame con la cantidad de turnos deseados por empleado.
        total_requerimientos_df (pd.DataFrame): DataFrame con el total de empleados necesarios por turno.

    Returns:
        tuple: Una tupla que contiene:
            - prob (LpProblem): El objeto LpProblem resuelto.
            - x (dict): Variables de decisión de asignación de empleados a turnos.
            - y (dict): Variables de decisión si el empleado trabaja en un día dado.
            - w (dict): Variables de decisión si el empleado descansa en un día dado.
            - z (dict): Variables de decisión si el empleado hace doble turno en un día dado.
            - aux (LpVariable): Variable auxiliar para el balanceo de carga.
            - P (dict): Parámetro de preferencias (costos).
            - B (dict): Parámetro de habilidades.
            - Q_val (dict): Parámetro de requisitos totales de empleados por turno.
            - U_val (dict): Parámetro de turnos deseados por empleado.
            - dias_zimpl_indices (list): Lista de índices numéricos para los días.
    """
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    shifts = ["TM", "TT"] # Turno Mañana, Turno Tarde
    turnos = [f"{day} {shift}" for day in days for shift in shifts]


    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    print("************************************** CHEQUEAR *********************************************")
    print("Tipo y forma de habilidades_df")
    print(type(habilidades_df))
    print(habilidades_df.shape)
    print(habilidades_df.index)
    print(habilidades_df.columns)
    print(habilidades_df.dtypes)
    print("Primera fila:")
    print(habilidades_df.iloc[0])
    print("************************************** CHEQUEAR *********************************************")


    # --- 1. Definición de Parámetros (desde los DataFrames) ---

    # PARAMETRO Q[Turnos]: Cuántos empleados necesito en cada turno (total)
    # `total_requerimientos_df` tiene 'Turno' como índice y 'Empleados Necesarios' como columna.
    # Convertimos a un diccionario para que PuLP lo use fácilmente: Q_val['Lunes TM'] = 3
    Q = total_requerimientos_df['Empleados Necesarios'].to_dict()

    # PARAMETRO U[Empleados]: Cuántos turnos tiene que hacer cada empleado
    # `turnos_deseados_df` tiene 'Empleado' como índice y 'Turnos Deseados' como columna.
    # Convertimos a un diccionario: U_val['Juan'] = 5
    U = turnos_deseados_df['Turnos Deseados'].to_dict()

        # PARAMETRO D[Turnos*Empleados]: Si el empleado E está disponible en el turno T (0 o 1)
    # PARAMETRO P[Turnos*Empleados]: Preferencias de turnos para los empleados (0-5, donde menor es mejor).
    # Ahora, P mantiene el valor tal cual (0-5), y D indica disponibilidad (0 o 1).
    P = {}  # Diccionario de preferencias (costos) por empleado
    D = {}  # Diccionario de disponibilidad por empleado




    for turno_str, prefs_empleados in preferencias_df.to_dict('index').items():
        for empleado_str, pref_val in prefs_empleados.items():
            if empleado_str not in P:
                P[empleado_str] = {}
                D[empleado_str] = {}

            # Disponibilidad
            D[empleado_str][turno_str] = 1 if pref_val > 0 else 0

            # Preferencia
            P[empleado_str][turno_str] = pref_val
    
    B = habilidades_df.T.astype(int).to_dict(orient='dict')

    V= requisitos_roles_df.to_dict()
   

    # --- 2. Definición del Problema de Optimización con PuLP ---
    prob = LpProblem("Planificacion_Turnos", LpMinimize)

    # --- 3. Variables de Decisión ---
    # x[Turnos*Empleados] binary; # 1 si el empleado E trabaja en el turno T
    x = LpVariable.dicts("Trabaja", (turnos, empleados), 0, 1, LpBinary)

    # y[Dias*Empleados] binary; # 1 si el empleado E trabaja en el dia M (TM o TT o ambos)
    # Indexado por los números de día de ZIMPL (0, 2, ...)
    y = LpVariable.dicts("TrabajaDia", (days, empleados), 0, 1, LpBinary)

    # w[Dias*Empleados] binary; # 1 si empleado E se toma vacaciones el dia M (descansa)
    # Indexado por los números de día de ZIMPL
    w = LpVariable.dicts("DescansaDia", (days, empleados), 0, 1, LpBinary)

    # z[Dias*Empleados] binary; # 1 si el empleado E hace doble turno el dia M (TM y TT)
    # Indexado por los números de día de ZIMPL
    z = LpVariable.dicts("DobleTurno", (days, empleados), 0, 1, LpBinary)

    # aux integer; # Variable auxiliar para balancear el mínimo de turnos asignados
    aux = LpVariable("AuxiliarMinTurnos", lowBound=0  ,cat='Integer')

    # --- 4. Función Objetivo ---
    # minimize cost: sum <t> in Turnos: sum <e> in Empleados: x[t,e] * P[t,e] + aux;
    # La restricción D[t,e] >= x[t,e] asegurará que x[t,e] será 0 si D[t,e] es 0 (indisponible).
    # Por lo tanto, el término P[t,e] para los turnos indisponibles será x[t,e]*0 = 0.

    
    objective_cost_term = lpSum(x[t][e] * P[t][e] for t in turnos for e in empleados)
    prob += objective_cost_term + aux, "Costo Total y Balanceo de Turnos"

    # --- 5. Restricciones ---

    # subto no_trabajar_turnos_de_mas: forall <e> in Empleados: U[e] == sum <t> in Turnos: x[t, e];
    # Cada empleado debe realizar el número de turnos deseado.
    for e in empleados:
        prob += lpSum(x[t][e] for t in turnos) == U[e], f"Turnos_totales_{e}"

    # subto no_trabajar_no_disponible: forall <t> in Turnos: forall <e> in Empleados: D[t, e] >= x[t, e];
    # Un empleado solo puede ser asignado a un turno si está disponible (D[t,e] = 1).
    for t in turnos:
        for e in empleados:
            prob += D[t][e] >= x[t][e], f"Disponibilidad_{e}_{t}"

     # subto cubrir_demanda: forall <t> in Turnos: Q[t] <= sum <e> in Empleados: x[t, e];
    # Cubrir la demanda total de empleados por turno.
    for t in turnos:
        prob += lpSum(x[t][e] for e in empleados) >= Q[t], f"Cubrir_demanda_total_{t}"


    # --- Restricciones de DOBLE TURNO (z) ---
    # ligar_variable4 y ligar_variable5:
    # z[m, e] es 1 si el empleado E trabaja en el turno 'm' (TM) y 'm+1' (TT) del mismo día.
    # Aquí 'm' son los índices numéricos de días de ZIMPL (0, 2, ...)
    for m in days: # Itera a través de los índices de turnos de mañana (0, 2, ..., 12)
        t_tm_str = f'{m} TM'  # Nombre del turno de la mañana (ej: "Lunes TM")
        t_tt_str = f'{m} TT' # Nombre del turno de la tarde (ej: "Lunes TT")

        for e in empleados:
            # z[m][e] = 1 si x[t_tm_str][e] y x[t_tt_str][e] son 1 (trabaja ambos turnos)
            prob += z[m][e] <= x[t_tm_str][e], f"DobleTurno_def_1_{m}_{e}"
            prob += z[m][e] <= x[t_tt_str][e], f"DobleTurno_def_2_{m}_{e}"
            prob += x[t_tm_str][e] + x[t_tt_str][e] <= z[m][e] + 1, f"DobleTurno_def_3_{m}_{e}"


    # --- Restricciones de UN FRANCO (y, w) ---
    # ligar_variable1 y ligar_variable2:
    # y[m, e] es 1 si el empleado E trabaja en CUALQUIER turno (TM o TT) del día 'm'.
    for m in days: # Itera a través de los índices de turnos de mañana (0, 2, ..., 12)
        t_tm_str = f'{m} TM'  # Nombre del turno de la mañana (ej: "Lunes TM")
        t_tt_str = f'{m} TT' # Nombre del turno de la tarde (ej: "Lunes TT")

        for e in empleados:
            prob += y[m][e] >= (x[t_tm_str][e] + x[t_tt_str][e]) / 2, f"TrabajaDia_def_1_{m}_{e}"
            prob += y[m][e] <= (x[t_tm_str][e] + x[t_tt_str][e]), f"TrabajaDia_def_2_{m}_{e}"


    # ligar_variable3: y[m, e] + w[m, e] == 1;
    # w[m,e] es 1 si el empleado E descansa el día 'm'.
    for m in days:
        for e in empleados:
            prob += y[m][e] + w[m][e] == 1, f"Descanso_Trabajo_def_{m}_{e}"

    # un_franco: forall <e> in Empleados: sum <m> in Dias: w[m, e] >= 1;
    # Cada empleado debe tener al menos un día de descanso (w[m,e] == 1) a la semana.
    for e in empleados:
        prob += lpSum(w[m][e] for m in days) >= cantidad_de_francos, f"Al_menos_un_franco_{e}"

    for e in empleados:
        prob += lpSum(z[m][e] for m in days) <= cantidad_de_dobles, f"Al_menos_un_doble_{e}"


    # --- Restricciones de CUBRIR ROLES (V) ---
    # cumplir_roles: forall <t> in Turnos: forall <r> in Roles: sum <e> in Empleados: x[t, e] * B[r, e] >= V[t, r];
    # Asegura que la cantidad de empleados asignados a un rol específico en un turno sea igual o mayor a la demanda.
    for t_str in turnos: # Itera a través de los nombres de los turnos (strings)
        for r_str in roles: # Itera a través de los nombres de los roles (strings)
            # V[t_str][r_str] es el acceso correcto al diccionario V
            prob += lpSum(x[t_str][e] * B[r_str][e] for e in empleados) >= V[t_str][r_str], f"Roles_cubiertos_{t_str}_{r_str}"


    # --- Restricciones de BALANCEO DE CARGA (aux) ---
    # emparejar: forall <e> in Empleados: sum <t> in Turnos: x[t, e] >= aux;
    # La cantidad de turnos asignados a cada empleado debe ser al menos 'aux'.
    # Como queremos maximizar 'aux' (es parte de la función objetivo, que minimiza -aux),
    # esto ayuda a balancear la carga de trabajo.
    for e in empleados:
        prob += lpSum(x[t][e] for t in turnos) >= aux, f"Balanceo_min_turnos_{e}"

    return prob, x, y, w, z, aux, P, B, Q, U
