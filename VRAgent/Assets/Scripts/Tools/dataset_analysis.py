import pandas as pd

# Load data
df = pd.read_csv("dataset_summary.csv")

# Columns for statistics
metrics = ["Scripts", "LOC", "Files", "Scenes", "GOs"]

print("=" * 50)
print("Overall Statistics")
print("=" * 50)

for col in metrics:
    print(f"\n[{col}]")
    print(f"  Min   : {df[col].min()}")
    print(f"  Max   : {df[col].max()}")
    print(f"  Mean  : {df[col].mean():.2f}")
    print(f"  Median: {df[col].median():.2f}")


print("\n" + "=" * 50)
print("Group-wise Statistics")
print("=" * 50)

grouped = df.groupby("Group")

for group, gdf in grouped:
    print(f"\n### {group} ###")

    for col in metrics:
        print(f"\n[{col}]")
        print(f"  Min   : {gdf[col].min()}")
        print(f"  Max   : {gdf[col].max()}")
        print(f"  Mean  : {gdf[col].mean():.2f}")
        print(f"  Median: {gdf[col].median():.2f}")
