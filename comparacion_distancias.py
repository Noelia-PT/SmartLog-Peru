import pandas as pd
import heapq as hq
import time
import math

#nodo origen obvio
ORIGEN = "A_1"

#especialidades qpara las que se quiere la ruta
#el orden lo decide el algoritmo 
#se cmabia para probar otras opciones  
ESPECIALIDADES_OBJETIVO = [
    "Colchones",
    "Electrodomesticos",
    "Herramientas"
]

#dataset con los pesos de las aristas calculados por 3 metodos 
ARCHIVOS_ARISTAS = {
    "Manhattan": "Dataset_aristas_Manhattan.csv",
    "Euclidiana": "Dataset_aristas_Euclidiana.csv",
    "Haversine": "Dataset_aristas_Haversine.csv",
}

ARCHIVO_NODOS = "Dataset_Nodos.csv"


# Heuristicas que intentan "adivinar" jiji que tan lejos está un nodo de otro 

def heuristica_manhattan(coords, u, t):
    xu, yu = coords[u]
    xt, yt = coords[t]
    return (abs(xu - xt) + abs(yu - yt))*100
 
 
def heuristica_euclidiana(coords, u, t):
    xu, yu = coords[u]
    xt, yt = coords[t]
    return (math.sqrt((xu - xt) ** 2 + (yu - yt) ** 2))*100
 
 
def heuristica_haversine(coords, u, t):
    R = 6371.0
    xu, yu = coords[u]
    xt, yt = coords[t]
 
    lat1, lon1 = math.radians(xu), math.radians(yu)
    lat2, lon2 = math.radians(xt), math.radians(yt)
 
    dlat = lat2 - lat1
    dlon = lon2 - lon1
 
    h = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
 
    return 2 * R * math.asin(math.sqrt(h))

# elegir heuristica según el nombre 
HEURISTICAS = {
    "Manhattan": heuristica_manhattan,
    "Euclidiana": heuristica_euclidiana,
    "Haversine": heuristica_haversine,
}

def construir_grafo(aristas):
    # G como: { "A_1": [("A_2", 158), ("A_3", 311)], "A_2": [...], ... }
    #diccionario 
    G = {}
 
    for _, fila in aristas.iterrows():
        u = fila["ID_Origen"]
        v = fila["ID_Destino"]
        w = fila["Costo"]

        #grafo no dirigido, se va en ambos sentidos 
        G.setdefault(u, []).append((v, w))
        G.setdefault(v, []).append((u, w)) 
 
    return G

def construir_coords(nodos):
    # { "A_1": (-12.046, -77.126), ...}
    coords = {}
    for _, fila in nodos.iterrows():
        coords[fila["ID_Nodo"]] = (fila["X"], fila["Y"])
    return coords

def a_estrella(G, s, t, coords, heuristica):
    """
    La cola de prioridad no ordena por 'g' (costo real), sino por
    'f = g + h' (costo real + heurística hacia el destino t).
    cost[] guarda el costo real (g), no f. f solo se usa
    para decidir el orden de exploración, nunca se guarda como costo final.
    """

    """
    s = nodo donde arranca la busqueda (nodo origen)
    t = nodo destino 
    u = nodo actual 
    v = vecinos de u
    w = peso 
    """
    #nodos de los que sabemos su costo minimo 
    visited = set()
    path = {}
    #costo real mas barato 
    cost = {s: 0}
 
    pqueue = [(heuristica(coords, s, t), s)]
 
    # cuando aun hay nodos por explorar 
    while pqueue:
        #se saca de la cola el nodo con menor f=g+h 
        f_u, u = hq.heappop(pqueue)
 
        if u in visited:
            continue
 
        #cost[u] es costo minimo real 
        visited.add(u)
 
        #si ya llegamos al destino la cortamos 
        if u == t:
            break
 
        #revisar los vecinos de u
        for v, w in G.get(u, []):
            if v not in visited:
                
                g = cost[u] + w  # costo real acumulado hasta v, pasando por u
 
                #este camino hacia v es mejor?
                if g < cost.get(v, math.inf):
                    cost[v] = g
                    path[v] = u
                    #metemos a la cola (f,v) y así la cola prioriza los nodos que además de ser baratos están
                    #supuestamente mas cerca al destino gracias a la heuristica 
                    f = g + heuristica(coords, v, t)  
                    hq.heappush(pqueue, (f, v))
 
    return path, cost

def reconstruir_camino(path, s, t):
    # 'path' guarda, para cada nodo, quién fue su "padre" en el mejor camino encontrado
    # Para armar la ruta completa hay que ir de t hacia atrás hasta llegar a s, y después invertir la lista
    # para obtener el orden correcto desde el origen 
 
    if t != s and t not in path:
        return None  # no existe camino de s a t
 
    camino = [t]
    actual = t
 
    while actual != s:
        actual = path[actual]
        camino.append(actual)
 
    camino.reverse()
    return camino


# vecino mas cercanooo
# se decide solo el siguiente paso
def siguiente_especialidad_mas_cercana(G, nodos, coords, heuristica, origen, especialidades_pendientes):
    mejor_nodo = None
    mejor_especialidad = None
    # infinito primero para que al inicar cualquier candidato se el mejor 
    mejor_costo = float("inf")

    #especilidades que aún faltan visitar 
    for especialidad in especialidades_pendientes:

        candidatos = nodos[nodos["Especialidad"] == especialidad]

        for _, fila in candidatos.iterrows():

            nodo = fila["ID_Nodo"]

            _, cost = a_estrella(G, origen, nodo, coords, heuristica)
 
            if nodo in cost and cost[nodo] < mejor_costo:
                mejor_costo = cost[nodo]
                mejor_nodo = nodo
                mejor_especialidad = especialidad
    
    #se devuelve el almacén mas barato entre todos
    return mejor_nodo, mejor_especialidad, mejor_costo

# se arma la ruta completa 
def calcular_ruta(G, nodos,coords,heuristica, origen, especialidades_objetivo):
    #lista de nodos visitados 
    ruta_total = [] 
    #suma de costos 
    costo_total = 0
    #nodo en lq eu nos quedaremos en cada iteracion
    actual = origen
    pendientes = set(especialidades_objetivo)

    # mmientras quedan especilidades sin visitar se ejecuta lo siguiente 
    while len(pendientes) > 0:

        #almacen mas barato de alcanzr desde actual 
        siguiente_nodo, especialidad, costo = siguiente_especialidad_mas_cercana(
            G, nodos,coords, heuristica, actual, pendientes
        )

        if siguiente_nodo is None:
            raise ValueError(
                f"No se encontró ruta para las especialidades restantes: {pendientes}"
            )
 
        # corremos a_estrella otra vez (para tener 'path') y reconstruimos el camino nodo por nodo
        path, _ = a_estrella(G, actual, siguiente_nodo, coords, heuristica)
        tramo = reconstruir_camino(path, actual, siguiente_nodo)

        if len(ruta_total) == 0:
            ruta_total.extend(tramo)
        else:
            ruta_total.extend(tramo[1:])

        #sumamos el cste del tramo al coste total 
        costo_total += costo
        #sacamos la especialidad en la que encontramos el camino corto de las especilidades pendintes 
        pendientes.remove(especialidad)
        # el nodo actual será l que acabamos de visitar 
        actual = siguiente_nodo

    return ruta_total, costo_total

def main():

    nodos = pd.read_csv(ARCHIVO_NODOS, sep=",")
    coords = construir_coords(nodos)

    #meramente estetico 
    print("=" * 60)
    print("COMPARACIÓN DE MÉTRICAS DE DISTANCIA (A*)")
    print("=" * 60)
    print(f"Origen: {ORIGEN}")
    print(f"Especialidades objetivo: {ESPECIALIDADES_OBJETIVO}")
    print("=" * 60)

    #se guarda suta costo tiempo 
    resultados = {}

    for nombre_metrica, archivo_aristas in ARCHIVOS_ARISTAS.items():

        #archivo de aristas correspondinte a la metrica 
        aristas = pd.read_csv(archivo_aristas, sep=",")
        G = construir_grafo(aristas)

        #elegir heuristica dependiendo de la metric 
        heuristica = HEURISTICAS[nombre_metrica]

        inicio = time.time()

        try:
            ruta, costo_total = calcular_ruta(
                G, nodos, coords, heuristica, ORIGEN, ESPECIALIDADES_OBJETIVO
            )
            error = None
        except ValueError as e:
            ruta, costo_total = [], None
            error = str(e)

        fin = time.time()
        tiempo = fin - inicio

        resultados[nombre_metrica] = {
            "ruta": ruta,
            "costo_total": costo_total,
            "tiempo": tiempo,
            "error": error
        }

        print(f"\n{nombre_metrica}: ")

        if error:
            print(f"Error: {error}")
        else:
            print(f"Ruta: {' -> '.join(ruta)}")
            print(f"Costo total: {round(costo_total, 2)}")

        print(f"Tiempo de ejecución: {round(tiempo, 6)} s")

if __name__ == "__main__":
    main()