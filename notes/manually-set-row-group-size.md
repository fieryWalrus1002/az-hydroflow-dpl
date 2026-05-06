# Manually setting Parquet Row Group Size

When we want to experiment with how Parquet performs with different size of Row Group, we can do so in pandas:

``` Python
import pandas as pd

# Convert your validated Pydantic data list to a DataFrame
df = pd.DataFrame(validated_records)

# Write to Parquet using pyarrow, forcing a specific row group limit
# (e.g., limit by number of rows to simulate row group boundaries locally)
df.to_parquet(
    "data/silver/example_validated_data.parquet",
    engine="pyarrow",
    row_group_size=100000,  # Forces pyarrow to cut a new row group every 100k rows
    compression="snappy"
)
```

 could use this to tune perofrmance in multi-GB datasets in Azure Synapse later.
