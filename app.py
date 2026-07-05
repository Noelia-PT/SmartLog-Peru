import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile
import time
import heapq as hq
import math

# texto para ejecutar el proyecto "streamlit run app.py"
# ==========================
# CONFIGURACIÓN
# ==========================

st.set_page_config(
    page_title="Sistema Logístico Nacional",
    layout="wide"
)

st.markdown("""
<style>

[data-testid="stSidebar"] {
    background-color: #1E293B;
}

[data-testid="stSidebar"] * {
    color: white;
}

</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1,4])

with col1:
    st.image(
        "https://cdn-icons-png.flaticon.com/512/854/854878.png",
        width=180
    )

with col2:
    st.title("SmartLog Perú")
    st.subheader(
        "Sistema Inteligente de Optimización Logística"
    )

# ==========================
# CARGAR DATOS
# ==========================

@st.cache_data
def cargar_datos():

    nodos = pd.read_csv(
        "Dataset_Nodos.csv",
        sep=","
    )

    aristas = pd.read_csv(
        "Dataset_aristas_Manhattan.csv",
        sep=","
    )

    return nodos, aristas

nodos, aristas = cargar_datos()

# ==========================
# CONSTRUIR GRAFO
# ==========================

@st.cache_resource
def construir_grafo(nodos, aristas):

    G = nx.Graph()

    for _, fila in nodos.iterrows():

        G.add_node(
            fila["ID_Nodo"],
            ubicacion=fila["Ubicacion"],
            especialidad=fila["Especialidad"],
            x=fila["X"],
            y=fila["Y"]
        )

    for _, fila in aristas.iterrows():

        G.add_edge(
            fila["ID_Origen"],
            fila["ID_Destino"],
            weight=fila["Costo"]
        )

    return G

G = construir_grafo(nodos, aristas)

def heuristica(G, a, b):

    xa = G.nodes[a]["x"]
    ya = G.nodes[a]["y"]

    xb = G.nodes[b]["x"]
    yb = G.nodes[b]["y"]

    #distancia Manhattan 
    return abs(xa - xb) + abs(ya - yb)

def a_estrella(G, s, t):

    visited = set()
    path = {}
    cost = {s: 0}

    # (f, nodo) en la cola de prioridad, con f = g + h
    pqueue = [(heuristica(G, s, t), s)]

    while pqueue:

        f_u, u = hq.heappop(pqueue)

        if u in visited:
            continue

        visited.add(u)

        if u == t:
            break

        for v in G.neighbors(u):

            if v not in visited:

                w = G[u][v]["weight"]
                g = cost[u] + w

                if g < cost.get(v, math.inf):

                    cost[v] = g
                    path[v] = u

                    f = g + heuristica(G, v, t)
                    hq.heappush(pqueue, (f, v))

    return path, cost


def reconstruir_camino(path, s, t):

    if t != s and t not in path:
        return None

    camino = [t]
    actual = t

    while actual != s:
        actual = path[actual]
        camino.append(actual)

    camino.reverse()
    return camino

#funcion para cuando solo se necesita el costo y no la ruta 
def a_estrella_costo(G, s, t):
    _, cost = a_estrella(G, s, t)
    return cost.get(t, math.inf)

#funcion para cuando se necesita la ruta complet 
def a_estrella_ruta(G, s, t):
    path, _ = a_estrella(G, s, t)
    return reconstruir_camino(path, s, t)

def visualizar_ruta(G, ruta, almacenes_objetivo=None):

    net = Network(
        height="700px",
        width="100%",
        directed=True
    )

    # NODOS
    for nodo in ruta:

        color = "lightblue"
        #diferenciar los colores de los nodos de los almacenes que pone el usuario
        if almacenes_objetivo and nodo in almacenes_objetivo:
            color = "orange"

        if nodo == ruta[0]:
            color = "green"

        elif nodo == ruta[-1]:
            color = "red"

        info = nodos[
            nodos["ID_Nodo"] == nodo
        ].iloc[0]
        
        #al pasar el cursor sale la info de cada almacen 
        net.add_node(
            nodo,
            label=nodo,
            color=color,
            title=(
                f"Ubicación: {info['Ubicacion']}\n"
                f"Especialidad: {info['Especialidad']}\n"
                f"X: {info['X']}\n"
                f"Y: {info['Y']}"
            )
        )

    # ARISTAS DE LA RUTA
    for i in range(len(ruta)-1):

        net.add_edge(
            ruta[i],
            ruta[i+1],
            color="red",
            width=5
        )

    archivo = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".html"
    )

    net.save_graph(archivo.name)

    html = open(
        archivo.name,
        encoding="utf-8"
    ).read()

    st.components.v1.html(
        html,
        height=700
    )

def buscar_almacen_mas_cercano(
    G,
    nodos,
    origen,
    especialidad
):

    candidatos = nodos[
        nodos["Especialidad"] == especialidad
    ]

    mejor_nodo = None
    mejor_costo = float("inf")

    for _, fila in candidatos.iterrows():

        nodo = fila["ID_Nodo"]

        try:

            costo = a_estrella_costo(
                G,
                origen,
                nodo
            )

            if costo < mejor_costo:

                mejor_costo = costo
                mejor_nodo = nodo

        except:

            pass

    return mejor_nodo

def siguiente_especialidad_mas_cercana(
    G,
    nodos,
    origen,
    especialidades_pendientes
):

    mejor_nodo = None
    mejor_especialidad = None
    mejor_costo = float("inf")

    for especialidad in especialidades_pendientes:

        candidatos = nodos[
            nodos["Especialidad"] == especialidad
        ]

        for _, fila in candidatos.iterrows():

            nodo = fila["ID_Nodo"]

            try:

                costo = a_estrella_costo(
                    G,
                    origen,
                    nodo
                )

                if costo < mejor_costo:

                    mejor_costo = costo
                    mejor_nodo = nodo
                    mejor_especialidad = especialidad

            except nx.NetworkXNoPath:
                pass

    return (
        mejor_nodo,
        mejor_especialidad,
        mejor_costo
    )

# ==========================
# SIDEBAR
# ==========================

menu = st.sidebar.radio(
    "Menú",
    [
        "Inicio",
        "Buscar Ruta",
        "Buscar Especialidad",
        "Visualizar Grafo"
    ]
)

# ==========================
# INICIO
# ==========================

if menu == "Inicio":

    st.markdown("""
    ## Bienvenido a SmartLog Perú

    Optimice rutas logísticas a nivel nacional utilizando
    algoritmos avanzados de búsqueda y teoría de grafos.

    ### Funcionalidades
                
    El sistema destaca por su capacidad de realizar una 
    búsqueda de rutas óptimas y lograr la optimización 
    de recorridos, lo que permite maximizar la eficiencia 
    en los traslados y reducir tiempos de ejecución. 
    Además, integra una herramienta de visualización 
    interactiva de grafos que facilita la interpretación 
    de las redes y conexiones de forma dinámica y visual.
                
    """)

    st.image(
        "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d",
        use_container_width=True
    )

    st.subheader("Resumen de la Red")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Nodos",
        G.number_of_nodes()
    )

    c2.metric(
        "Aristas",
        G.number_of_edges()
    )

    c3.metric(
        "Componentes",
        nx.number_connected_components(G)
    )

    c4.metric(
        "Especialidades",
        nodos["Especialidad"].nunique()
    )

    st.markdown("---")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.info(
            """
            Transporte Nacional
            
            Cobertura de almacenes en todo el país.
            """
        )

    with c2:
        st.success(
            """
            Optimización
            
            Rutas calculadas mediante A* y teoría de grafos.
            """
        )

    with c3:
        st.warning(
            """
            Especialidades
            
            Más de 100 categorías de almacenes.
            """
        )


# ==========================
# BUSCAR RUTA
# ==========================

elif menu == "Buscar Ruta":

    st.subheader("Ruta Óptima")

    origen = "A_1"
    st.info("Origen: Callao (A_1)")

    if "especialidades" not in st.session_state:
        st.session_state["especialidades"] = []

    productos = st.multiselect(
        "Especialidades requeridas",
        sorted(nodos["Especialidad"].unique()),
        key="especialidades"
    )

    if st.button("Limpiar selección"):

        del st.session_state["especialidades"]

        st.rerun()

    st.info(
        "El último almacén visitado será el destino final."
    )

    st.info(
        "Algoritmo utilizado: A* con heurística Manhattan"
    )

    if st.button("Calcular Ruta"):

        inicio = time.time()

        if len(productos) == 0:

            st.warning(
                "Seleccione al menos una especialidad."
            )

            st.stop()

        ruta_total = []
        costo_total = 0

        actual = origen

        pendientes = set(productos)

        especialidades_visitadas = []
        almacenes_visitados = []
        while len(pendientes) > 0:

            siguiente_nodo, especialidad, costo = (
                siguiente_especialidad_mas_cercana(
                    G,
                    nodos,
                    actual,
                    pendientes
                )
            )

            if siguiente_nodo is None:

                st.error(
                    "No se encontró una ruta válida."
                )

                st.stop()

            tramo = a_estrella_ruta(
                G,
                actual,
                siguiente_nodo
            )

            if len(ruta_total) == 0:

                ruta_total.extend(tramo)

            else:

                ruta_total.extend(tramo[1:])

            costo_total += costo

            especialidades_visitadas.append(
                especialidad
            )

            almacenes_visitados.append(
                siguiente_nodo
            )

            pendientes.remove(
                especialidad
            )

            actual = siguiente_nodo

        fin = time.time()

        st.success("Ruta encontrada")

        st.write(
            "### Orden de visita optimizado"
        )

        for i, esp in enumerate(
            especialidades_visitadas,
            start=1
        ):

            st.write(
                f"{i}. {esp}"
            )

        st.write(
            "### Ruta completa"
        )

        st.write(
            " ➜ ".join(ruta_total)
        )

        visualizar_ruta(
            G,
            ruta_total,
            almacenes_visitados
        )

        st.write("### Detalle de la Ruta")

        datos_ruta = []

        for nodo in ruta_total:

            info = nodos[
                nodos["ID_Nodo"] == nodo
            ].iloc[0]

            tipo = "Intermedio"

            if nodo == ruta_total[0]:
                tipo = "Origen"

            elif nodo == ruta_total[-1]:
                tipo = "Destino Final"

            elif nodo in almacenes_visitados:
                tipo = "Almacén Seleccionado"

            datos_ruta.append({
                "Nodo": nodo,
                "Ubicación": info["Ubicacion"],
                "Especialidad": info["Especialidad"],
                "Tipo": tipo
            })

        tabla_ruta = pd.DataFrame(datos_ruta)

        st.dataframe(
            tabla_ruta,
            use_container_width=True
        )

        ultimo_nodo = ruta_total[-1]

        info_final = nodos[
            nodos["ID_Nodo"] == ultimo_nodo
        ].iloc[0]

        st.success(
            f"Destino final: "
            f"{info_final['Ubicacion']} "
            f"({ultimo_nodo})"
        )

        st.write(
            f"Especialidad final: "
            f"{info_final['Especialidad']}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Costo Total",
                round(costo_total, 2)
            )

        with col2:
            st.metric(
                "Tiempo de cálculo (s)",
                round(fin - inicio, 6)
            )

        with col3:

            if st.button("Nueva búsqueda :)"):

                for clave in list(st.session_state.keys()):

                    del st.session_state[clave]

                st.rerun()

# ==========================
# ESPECIALIDADES
# ==========================

elif menu == "Buscar Especialidad":

    st.subheader("Buscar Almacenes")

    lista = sorted(
        nodos["Especialidad"].unique()
    )

    especialidad = st.selectbox(
        "Especialidad",
        lista
    )

    resultado = nodos[
        nodos["Especialidad"] == especialidad
    ]

    st.dataframe(
        resultado[
            ["ID_Nodo",
             "Ubicacion",
             "Especialidad"]
        ]
    )

# ==========================
# VISUALIZAR GRAFO
# ==========================

elif menu == "Visualizar Grafo":

    st.subheader("Visualización de la Red")

    cantidad = st.slider(
        "Cantidad de nodos",
        20,
        500,
        100
    )

    muestra = nodos.head(cantidad)

    ids = set(muestra["ID_Nodo"])

    net = Network(
        height="700px",
        width="100%",
        directed=True
    )

    for _, fila in muestra.iterrows():

        net.add_node(
            fila["ID_Nodo"],
            title=(
                f"Ubicación: {fila['Ubicacion']}\n"
                f"Especialidad: {fila['Especialidad']}"
            ),
            label=fila["ID_Nodo"]
        )

    for _, fila in aristas.iterrows():

        if (
            fila["ID_Origen"] in ids
            and
            fila["ID_Destino"] in ids
        ):

            net.add_edge(
                fila["ID_Origen"],
                fila["ID_Destino"],
                title=str(fila["Costo"])
            )

    archivo = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".html"
    )

    net.save_graph(archivo.name)

    html = open(
        archivo.name,
        encoding="utf-8"
    ).read()

    st.components.v1.html(
        html,
        height=700
    )