# az-hydroflow-dpl

The **Azure Hydroflow Data Pipeline (az-hydroflow-dpl)** is a portfolio project designed to showcase my skills in data engineering, schema validation, and cloud-native infrastructure. The core objective is to ingest large datasets, validate them using Pydantic, and store them in the Parquet format ([docs here](https://parquet.apache.org/docs/overview/)) to demonstrate storage optimization for high-scale analytics.

## Project plan

All of my projects follow a similar workflow: plan, prototype, then incrementally implement. This is the planning part!

### Phase 1: Local data exploration using a notebook

The project will start with exploratory work in a Jupyter Notebook container deployed via Docker compose. We are using a Docker container to host the Jupyter notebook to ensure that our local development environment will be able to be duplicated exactly when we migrate to the cloud.

After establishing the data inputs, prototype the data validation using Pydantic before prototyping the transofmration logic. Use a medallion architecture.

* I'd like to implement at least two data streams, one streaming and one batched. The streaming data won't be able to be prototyped in a notebook well, but we can at least identify some data sources to ingest.
* Create schemas to serve as a contract for the raw incoming data. Pydantic will let me coerce the fields into the format I need, and validate the data before I place it into the data folders.
* Prototype the silver-layer processing of the raw bronze parquet files into the validated, partitioned Parquet files.
* Add in some error handling for the validation errors, with logging. Ideally prototpye some telemetry we can use later on for the whole pipeline. We want to know what happens, not just crash or silently fail to load data for days in a row.
  * Add in a dead-letter directory for failed data validation?
  * Can test with a valid data source, but an invalid schema to show that we can track this kind of thing.

#### Data sources

* [GEO Aqua Watch](https://www.geoaquawatch.org/water-quality-database-inventory/) has a wide array of datasets available.
* [EOSDIS Earthdata](https://urs.earthdata.nasa.gov)

#### Data folder layout

We need to start our data pipeline out right. Ensure we have a landing zone to keep the raw data, a dead-letter zone for failed validation, a standardized bronze layer for the parquet format with added metadata, and a silver for the clean, validated data files. We will continue this pattern later in the data lake.

| Layer | Action | Format |
| --- | --- | --- |
| Raw | Ingest | JSON/CSV |
| Bronze | Standardize | Parquet |
| Silver | Clean & Validate | Validated Parquet |
| Quarantine | Log Failures | JSON/Parquet |

In order to take advantage of the Parquet format, we will add `ingestion_timestamp` metadata and partition by a key in Bronze. The sooner we get those big csvs into a partitioned Parquet format, the more we'll gain in performance improvements during the validation and cleaning phases later.

#### Partitioning Strategy

Depending on how wide we cast our data nets, it may be advantageous to partition via timestamp, state, region, etc. How deeply we partition is going to depend on the downstream analytics workflows as well as how much data we end up ingesting. I've read that ideal partition sizes (row groups in Parquet terms) tend up between [512 MB to 1 GB in size](https://parquet.apache.org/docs/file-format/configurations/).

Good potential keys:

* `/year=YYYY/month=MM/` or `/region/`: Groups enough data together so that teh files written to ADLS2 are naturally large, allowing Parquet's inner Row Groups to compress and perform optimally.

Bad keys:

* `/timestamp=YYYY-MM-DD-HH-MM/`: You end up with thousands/millions of tiny, empty files.

Once we have a good enough dataset, we can experimentally find a good key for our partitioning strategy. We can [manually set Row Group size](notes/manually-set-row-group-size.md) with pandas/pyarrow to conduct this experiment.

#### Dev deployment

To start up our jupyter container:

``` bash
# Local dev:
# Run the docker compose to bring up our scipy container
docker compose up

# Should be able to connect to the notebook with this:
http://localhost:8888/?token={$JUPYTER_TOKEN}
```

### Phase 2: Transition logic and implement testing

If our notebook data ingestion is successful, it will be time to migrate our logic into a form that we will be able to containerize. This will involve several steps:

* move to a standard src/hydroflow layout
* implement a test suite for the logic
* establish CI/CD integration
* create orchestration layer... maybe app.py style?

### Phase 3: Initial Azure IaC Deployment

Once we have a working prototype locally, its time to move it onto the cloud. We'll use bicep for this, as the Azure-preferred method. If it was in the homelab, I'd be using Terraform.

#### Steps

* Identify the appropriate authentication flow. Managed Identities appeals, but Service Principals is an option as its aimed more at local to cloud dev.
* Define the infrastructure we need using the infra/*.bicep files.
* Start a notebook for interacting with the cloud data.
  * Repeat the data ingestion.
  * Ensure that the data lands in the appropriate locations on the data lake.

#### Deploy Infrastructure

Use Bicep to define these resources programmatically:

* ADLS2 storage
* Azure Key Vault to manage our secrets, as we will connect to the data lake via the notebook locally while we continue to develop. Pydantic has a BaseSettings option, so we'll explore that too.
* Other authentication tooling?

### Phase 4: Containerize and deploy

If we have a working data flow, we wrap it up into a container we can deploy on Azure. I haven't gotten far enough into the intricacies to know how to do this best.
