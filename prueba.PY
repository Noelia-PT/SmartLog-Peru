import pandas as pd

nodos = pd.read_csv(
    "Dataset_Nodos.csv",
    sep=","
)

aristas = pd.read_csv(
    "Dataset_aristas.csv",
    sep=","
)

print(nodos.head())
print()
print(aristas.head())