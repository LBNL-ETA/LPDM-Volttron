def execute_query(url, api_key, query):
    from smap.archiver.client import SmapClient
    
    if url[-1] != "/":
        url = url + "/"
    url = url + "backend"
    
    res = None
    try:
        c = SmapClient(url, key = api_key)
        
        res = c.query(query)
    except Exception as e:
        res = e
        print "Error:\t{s}".format(s = e)
    
    return res