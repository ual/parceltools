import psycopg2
import pandas as pd
import pandas.io.sql as sql
import numpy as np

conn_string = "dbname='national_data' user='postgres'"
conn = psycopg2.connect(conn_string)
cur = conn.cursor()

household_id = 1
field_names='serialno,state,county,tract,block,puma,household_id'
num_fields = 7
placeholder_s = '%s,%s,%s,%s,%s,%s,%s'

state_query = "select distinct st from pums2010_hh order by st"
states = sql.read_frame(state_query,conn)

for state_id in [27,6]:
    pumas_query = "select distinct puma from pums2010_hh where st = %s order by puma" % (state_id)
    pumas = sql.read_frame(pumas_query,conn)

    for puma in pumas.values:
        puma_id = puma[0]
        tracts_query = "select county_short,tract10 from tract_puma_xref where state= %s and puma2k = %s group by county_short,tract10 order by county_short, tract10" % (state_id,puma_id)
        tracts = sql.read_frame(tracts_query,conn)
        county_tract = zip(tracts.county_short.values,tracts.tract10.values)

        puma_hh_query = "select * from pums2010_hh where st=%s and puma = %s" % (state_id,puma_id)
        households = sql.read_frame(puma_hh_query,conn)
        households['county']=0
        households['tract']=0
        households['block']=0
        households['household_id']=0

        own1 = households[(households.np==1)*(households.ten<3)]
        own1 = own1[['serialno','st','county','tract','block','puma','household_id']]
        own2 = households[(households.np==2)*(households.ten<3)]
        own2 = own2[['serialno','st','county','tract','block','puma','household_id']]
        own3 = households[(households.np==3)*(households.ten<3)]
        own3 = own3[['serialno','st','county','tract','block','puma','household_id']]
        own4 = households[(households.np==4)*(households.ten<3)]
        own4 = own4[['serialno','st','county','tract','block','puma','household_id']]
        own5 = households[(households.np==5)*(households.ten<3)]
        own5 = own5[['serialno','st','county','tract','block','puma','household_id']]
        own6 = households[(households.np==6)*(households.ten<3)]
        own6 = own6[['serialno','st','county','tract','block','puma','household_id']]
        own7 = households[(households.np >7)*(households.ten<3)]
        own7 = own7[['serialno','st','county','tract','block','puma','household_id']]

        rent1 = households[(households.np==1)*(households.ten>2)]
        rent1 = rent1[['serialno','st','county','tract','block','puma','household_id']]
        rent2 = households[(households.np==2)*(households.ten>2)]
        rent2 = rent2[['serialno','st','county','tract','block','puma','household_id']]
        rent3 = households[(households.np==3)*(households.ten>2)]
        rent3 = rent3[['serialno','st','county','tract','block','puma','household_id']]
        rent4 = households[(households.np==4)*(households.ten>2)]
        rent4 = rent4[['serialno','st','county','tract','block','puma','household_id']]
        rent5 = households[(households.np==5)*(households.ten>2)]
        rent5 = rent5[['serialno','st','county','tract','block','puma','household_id']]
        rent6 = households[(households.np==6)*(households.ten>2)]
        rent6 = rent6[['serialno','st','county','tract','block','puma','household_id']]
        rent7 = households[(households.np >7)*(households.ten>2)]
        rent7 = rent7[['serialno','st','county','tract','block','puma','household_id']]

        households_by_category = [own1,own2,own3,own4,own5,own6,own7,rent1,rent2,rent3,rent4,rent5,rent6,rent7]
        var_ids = [109,110,111,112,113,114,115,117,118,119,120,121,122,123]
        households_by_category = zip(var_ids,households_by_category)

        for category in households_by_category:
            category_id = 'x' + str(category[0])
            matching_hh = category[1]
            
            for county, tract in county_tract:

                matching_hh['county'] = county
                matching_hh['tract'] = tract
                block_query = "select block, %s as num_households from segment44 where state = %s and county = %s and tract = %s" %(category_id,state_id,county,tract)
                blocks = sql.read_frame(block_query,conn)
                num_blocks = blocks.block.size
                
                for block in np.arange(num_blocks):
                    print "STATE: %s, PUMA: %s, COUNTY: %s, TRACT: %s, BLOCK: %s" % (state_id,puma_id,county,tract,block)
                    num_households = blocks.num_households[block]
                    if num_households > 0:
                        if matching_hh.serialno.size > 0:
                            sampler = np.random.randint(0, matching_hh.serialno.size, size=num_households)
                            draws=matching_hh.take(sampler)
                        else:
                            previous_draw = draws[:1]
                            draws_to_create = []
                            for hh in np.arange(num_households):
                                draws_to_create.append(previous_draw)
                            draws = pd.concat(draws_to_create)
                            draws['st']=state_id
                            draws['county']=county
                            draws['tract']=tract
                            draws['puma']=puma_id
                        draws['block']=blocks.block[block]
                        for hh in np.arange(num_households):
                            draws.household_id.values[hh]=household_id
                            household_id +=1
                        for idx,row in draws.iterrows():
                            i=0
                            to_tuple=[]
                            while i<num_fields:
                                to_tuple.append(row.values[i])
                                i=i+1
                            to_tuple=tuple(to_tuple)
                            insert_query="insert into popsyn_testing (" + field_names + ") values (" + placeholder_s + ")"
                            insert_query = (insert_query) % (to_tuple)
                            cur.execute(insert_query)
                            conn.commit()
                    
