import os
import psycopg2
import pandas as pd
import pandas.io.sql as sql
import numpy as np
import cStringIO

##DB settings
conn_string = "host='192.168.1.14' port= 5433 dbname='uscensus' user='urbanvision' password='Visua1ization'"
conn = psycopg2.connect(conn_string)
cur = conn.cursor()

#Identify geographies
state_fips_code = 6
county_fips_code = 19

#Query DB
jobs_query = "select * from lehd where statefp10 = %s and countyfp10 = %s" % (state_fips_code,str(county_fips_code))
jobs = sql.read_frame(jobs_query,conn)

print "data pulled from DB"

jobs = jobs[['countyfp10','tractce10','blockce','C000','CNS01','CNS02','CNS03','CNS04','CNS05','CNS06','CNS07','CNS08','CNS09','CNS10','CNS11','CNS12','CNS13','CNS14','CNS15','CNS16','CNS17','CNS18','CNS19','CNS20']]
    
sector_columns = ['CNS01','CNS02','CNS03','CNS04','CNS05','CNS06','CNS07','CNS08','CNS09','CNS10','CNS11','CNS12','CNS13','CNS14','CNS15','CNS16','CNS17','CNS18','CNS19','CNS20']

total_jobs = int(jobs.C000.sum())

#job_id = np.int32(np.arange(total_jobs) + 1)  #Just let the index serve this purpose

block_id = np.int32(np.zeros(total_jobs))

sector_id = np.int32(np.zeros(total_jobs))

state_id = np.int32(np.zeros(total_jobs))

county_id = np.int32(np.zeros(total_jobs))

tract_id = np.int32(np.zeros(total_jobs))

i = 0

for block in jobs.index.values:
    idx_block = np.where(jobs.index.values==block)
    tract = int(jobs['tractce10'].values[idx_block][0])
    county = int(jobs['countyfp10'].values[idx_block][0])
    blockid = int(jobs['blockce'].values[idx_block][0])
    for sector in sector_columns:
        num_jobs = int(jobs[sector].values[idx_block][0])
        if num_jobs > 0:
            j = i + num_jobs
            block_id[i:j]=blockid
            tract_id[i:j]=tract
            county_id[i:j]=county
            sector_num = int(sector[3:])                  
            sector_id[i:j]=sector_num
            i = j
            
jobs_table = {'block_id':block_id,'sector_id':sector_id,'county_id':county_id,'tract_id':tract_id}

jobs_table = pd.DataFrame(jobs_table)

jobs_table.index = jobs_table.index+1

#jobs_table['state_id'] = state_fips_code 

create_table_query = "create table jobs_fresno (job_id integer, block_id integer, sector_id integer, county_id integer, tract_id integer)"
cur.execute(create_table_query)
conn.commit()

output = cStringIO.StringIO()
jobs_table.to_csv(output, sep='\t', header=False)
output.seek(0)
print "stringio object created and written to"
cur.copy_from(output, 'jobs_fresno', columns =('job_id','block_id','county_id','sector_id','tract_id'))
conn.commit()
           