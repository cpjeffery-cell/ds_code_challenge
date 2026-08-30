
<img src="img/city_emblem.png" alt="City Logo"/>

# City of Cape Town - Data Science Unit Code Challenge

## How to Run This Submission

This submission targets the **Data Engineering** track (Steps 1, 2, and 5).

1. Install Python 3.12+ and the dependencies: `pip install -r requirements.txt`
2. Run the entry point from the repository root: `python scripts/main.py`

No credentials, environment variables, or other manual setup are required — AWS credentials and all external data (H3 polygons, service requests, the official suburb boundary, and the 2020 Atlantis wind workbook) are fetched automatically at runtime. The run completes with no human interaction and prints a labelled summary for each step (time taken, validation results, and pass/fail) to the console.

Each step also writes a log to `logs/`, and Step 5.3 writes its two CSV outputs to `output/` (excluded from git — see [docs/data_anonymisation.md](docs/data_anonymisation.md) for why). Supporting design decisions and validation methodology for each step are documented in [docs/](docs/), and the AI-assisted work log is in [AI_log.md](AI_log.md).

Unit tests can be run with: `python -m unittest discover -s tests`

`scripts/working_notebook.ipynb` is exploratory only and is not part of the graded submission; the reusable, tested implementation lives in `scripts/*.py`.

## Purpose

The purpose of this challenge is to evaluate the skills of prospective Data Scientists, Engineers, Analysts and Front End Developer for positions in the City of Cape Town's Data Science unit. 

## Intended audience

We will only evaluate responses to this challenge from people who we have requested to complete it. Of course, you are welcome to attempt it for your own enjoyment.

## Way of working and expected structure of submission
Principles of reproducible analysis and code versioning are very important to our workflow. Structuring your work to aid in reproducibility and readability is important. 

So, follow common conventions with respect to directory structure and names to make your work as easy to follow as possible.

## What we're looking for
### Expectation of Effort
We expect you to spend up to 48 calendar hours working on this assessment per position. If you are finding that you are spending significantly more time than this, then please contact whomever sent you the link to this assessment to let them know.

You should have received over 7 days warning that you would be undertaking this assessment. Please notify [Delyno du Toit](delyno.dutoit@capetown.gov.za) if this was not the case.

### Things to focus on
Over and above the tasks specified below, there are particular aspects of each position that we would like you to pay attention to:

* Data Engineer candidates - as the key enablers of our unit's work, we really want to see work done in a sustainable manner: writing for easy comprehension, testing, clean code, modularity all bring us joy.

### Candidates where programming is required (Data Scientist; Engineers, Visualisation Engineer and Front End Developers)
Requirements and notes:
* For Data Science and Data Engineering, our primary programming languages are `python`, `R` and `SQL`. We will accept code that is packaged in `.py`, `.ipynb`, `.R` and `.Rmd` files. Scripts in `.sql` may also be included where applicable.
* Bash or similar scripting language files are fine for glue. You may develop in any development environment you choose. 
* We expect to be able to clone your repo, immediately identify what script to execute from your README file, and execute it to completion with no human interaction. 
  In order to ensure that our environment has the right libraries or packages, please follow standard python (PEP8) or R guidelines for structure in your code, i.e place `import` and `library()` commands at the top of your scripts.
* If your repo does not clone and run, we will not attempt to fix it.
* If your analysis makes use of any external data, the data must either be included in the repo, or be downloaded automatically during script execution.


### Follow-on Questions
If we invite you to an interview, after completing and submitting this technical assessment, we will be asking follow-up 
questions about the work submitted. These questions might be at a very detailed level, or broadly conceptual, relating to 
the choices made in completing this assessment.

We do not expect perfect recall of what you may have submitted, but we do expect a deep knowledge of the content, and 
how it works.

### Use of Generative AI and/or Coding Agents
There is no restriction on the tools that you may use to complete this assessment. However we have tried to make the nature of this assessment within the scope of someone completing it without using AI assistance, as well as someone using them effectively.

If you do make use of Generative AI/Coding Agents, please include an `AI_log.md` where you log all of the work that you asked AI assistance to undertake, including any prompts, the model used as well number of tokens. It will be of considerable advantage if you can highlight or document at least one instance where the AI undertook work that you then corrected or improved upon.

## How to submit
### Candidates where programming is required (Data Scientist;  Engineers, Visualisation Engineers and Front End Developers)
1. Clone this repository and load it into your development environment. 
2. Work the challenge, committing regularly to document your progress. Try have structured, meaningful commits, where each one adds significant functionality in a coherent manner.
3. Host your repository somewhere that is publicly accessible. If you're using GitHub, please use a fork of our original repository.
4. Inform us via email that your challenge is complete, including a link to your repo. Be sure to make sure it is set to public.

**Be sure to 'watch' this repo for changes - we may push bugfixes**

NOTE: If you would like to _improve_ the content of this repository, by fixing typos or perhaps enhancing the challenge, please do so by submitting a pull request.

## Challenge
Follow the below steps, completing those indicated as relevant to the positions for which you are interviewing. If there are any steps that you can not complete after a reasonable amount of effort, rather move on to later steps, attempting everything relevant at least once.

For all roles, we expect the challenge response to include what you consider to be role-appropriate testing and validation. For example, a Data Scientist might want to include MAPE scores or confusion matrices. A Data Engineer may want to include logging and data quality validation tests, as well as unit and even integration tests. A Data Analyst might want to plot histograms of the data in question to ensure that outliers aren't overwhelming your analysis.

Your code should be well formatted according to generally accepted style guides and include whatever is necessary for a team-mate unfamiliar with it to maintain it.

### 0. Setup
#### Data
We have made the following datasets available (each filename is a link). These are all available in an AWS bucket `cct-ds-code-challenge-input-data`, in the `af-south-1` region, with the object name being the filenames below):
* [`sr.csv.gz`](https://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/sr.csv.gz) contains 12 months of service request data, where each row is a service request. A service request is a request from one of the residents of the City of Cape Town to undertake significant work. This is an important source of information on service delivery, and our performance thereof. *Note* as indicated by the extension, this file is compressed.
* [`sr_hex.csv.gz`](https://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/sr_hex.csv.gz) contains the same data as `sr.csv` as well as a column `h3_level8_index`, which contains the appropriate resolution level 8 H3 index for that request. If the request doesn't have a valid geolocation, the index value will be `0`. *Note* as indicated by the extension, this file is compressed.
* [`sr_hex_truncated.csv`](https://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/sr_hex_truncated.csv) is a truncated version of `sr_hex.csv`, containing only 3 months of data.
* [`city-hex-polygons-8.geojson`](https://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/city-hex-polygons-8.geojson) contains the [H3 spatial indexing system](https://h3geo.org/) polygons and index values for the bounds of the City of Cape Town, at resolution level 8.
* [`city-hex-polygons-8-10.geojson`](https://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/city-hex-polygons-8-10.geojson) contains the [H3 spatial indexing system](https://h3geo.org/) polygons and index values for resolution levels 8, 9 and 10, for the City of Cape Town.
* `swimming-pool-labels` (`s3://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/images/swimming-pool`) contains a random sample of aerial images from Cape Town, organised into two prefixes, `yes` or `no`, corresponding to whether there is a swimming pool in the image. Within each label prefix, there is a manifest file listing all the images available, i.e. [yes](https://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/images/swimming-pool/yes/manifest) and [no](https://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/images/swimming-pool/no/manifest).

In some of the tasks below you will be creating datasets that are similar to these, feel free to use the provided files to validate your work.

#### Dummy AWS Credentials
We have made AWS credentials available in the following file, with the appropriate permissions set, [here](https://cct-ds-code-challenge-input-data.s3.af-south-1.amazonaws.com/ds_code_challenge_creds.json).

*Note* These creds don't have any special access, other than what is already set on these resources for anonymous access. These are more provided to make using the various AWS client libraries easier.

### 1. Data Extraction (if applying for a Data Engineering Position)
Use the [AWS S3 SELECT](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-glacier-select-sql-reference-select.html) command to read in the H3 resolution 8 data from `city-hex-polygons-8-10.geojson`. Use the `city-hex-polygons-8.geojson` file to validate your work.

Please also add an additional validation that checks conformance to a reasonable schema for the dataset. The output of this validation should be a conformance "score" of some sort, with a non-binary threshold of your choice. Explicitly capture the desired schema used to compute this conformance score in a standalone configuration or documentation file.

Please log the time taken to perform the operations described as well as the validation steps, and within reason, try to optimise latency and computational resources used. Please also note the comments above about the nature of the code that we expect.

### 2. Initial Data Transformation (if applying for a Data Engineering, Visualisation Engineer, Front End Developer and/or Science Position)
Join the equivalent of the contents of the file `city-hex-polygons-8.geojson` to the service request dataset, such that each service request is assigned to a single H3 resolution level 8 hexagon. Use the `sr_hex.csv.gz` file to validate your work.

For any requests where the `Latitude` and `Longitude` fields are empty, set the index value to `0`. Use your judgement to include any other appropriate validation.

Include logging that lets the executor know how many of the records failed to join, and include a join error threshold above which the script will error out. Please motivate why you have selected the error threshold that you have. Please also log the time taken to perform the operations described, and within reason, try to optimise latency and computational resources used.

### 5. Further Data Transformations (if applying for a Data Engineering Position)
1. Create a subsample of the data by selecting all of the requests in `sr_hex.csv.gz` which are within 1 minute of the centroid of an official suburb in the proximity of Atlantis in the North of the City of Cape Town's bounds. You may determine the centroid of the suburb by the **computational** method of your choice (i.e. do not just hard code the value), but if any external data is used, your code should programmatically download and perform the centroid calculation. Please clearly document your method.

2. Augment your filtered subsample of `sr_hex.csv.gz` from (1) with the appropriate [wind direction and speed data for 2020](https://www.capetown.gov.za/_layouts/OpenDataPortalHandler/DownloadHandler.ashx?DocumentName=Wind_direction_and_speed_2020.ods&DatasetDocument=https%3A%2F%2Fcityapps.capetown.gov.za%2Fsites%2Fopendatacatalog%2FDocuments%2FWind%2FWind_direction_and_speed_2020.ods) from the Atlantis Air Quality Measurement site, from when the notification was created. All of the steps for downloading and preparing the wind data, as well as the join should be performed programmatically within your script. This endpoint can be unreliable - please add an appropriate strategy for handling this, with commentary for why you chose this approach for handling an unreliable dependency.

3. Write a script which anonymises your augmented subsample from (2), but preserves the following precisions (You may use H3 indice or lat/lon coordinates for your spatial data):
   * location accuracy to within approximately 500m
   * temporal accuracy to within 6 hours
   * Any records or columns which you believe could lead to the resident who made the request being identified despite the restrictions made above. For the records removed, make provision for a separate review by a person to anonymise the data by hand.
We expect in the accompanying report that you will justify as to why this data is now anonymised. Please limit this commentary to less than 500 words. If your code is written in a code notebook such as Jupyter notebook or Rmarkdown, you can include this commentary in your notebook.


## Contact
You can contact gordon.inggs, muhammed.ockards, kathryn.mcdermott and/or colinscott.anthony @ capetown.gov.za for any questions on the above.
