from bs4 import BeautifulSoup
import re
import json
import sys
import os
import MySQLdb
import MySQLdb.cursors
from credentials import *

def get_links(content):
    return [{"name": part.text.strip().title(), "id": part["href"].replace("view.jsp?id=", "").strip()} for part in content.find_all("a")]


def get_refs(content):
    refs = []
    for ref in content:
        if ref["class"][0] == "ref":
            cleaned = re.sub(" +", " ", ref.text.replace("[Link to electronic copy]", "").strip()).replace("\n", "")
            link = ref.find_all("a")
            url = ""
            if link:
                url = link[0]["href"].strip()
            refs.append({
                "name": cleaned,
                "url": url
            })
    return refs


def clean(content) :
    return re.sub(" +", " ", content.replace("\n", "").strip())


def get_areas(content):
    return re.sub(" +", " ", content.text.strip()).replace("\n", "").replace("  ", ", ")


def get_name(content):
    return {
        "name": re.sub("(\(.+\)|\[.+\])", "", content.text).strip().title(),
        "usage": ", ".join([re.sub("(\(|\)|\[|\])", "", use) for use in re.findall("(\(.+\)|\[.+\])", content.text.strip().title())])
    }


def new_name():
    return {
        "orig_id": "",
        "name": "",
        "usage": "",
        "type": "",
        "area": "",
        "comments": "",
        "age": "",
        "see_also": "",
        "refs": ""
    }


def insert_hierarchy(a, mtype, b):
    cursor.execute("""
        INSERT INTO nz_strat_tree (this_name, rel, that_name) VALUES (
            %(this_name)s,
            %(rel)s,
            %(that_name)s
        )
    """, {
        "this_name": a,
        "rel": mtype,
        "that_name": b
    })


try:
  connection = MySQLdb.connect(host=mysql_host, user=mysql_user, passwd=mysql_passwd, db=mysql_db, cursorclass=MySQLdb.cursors.DictCursor)
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

# Cursor for MySQL
cursor = connection.cursor()

# Clean up any leftovers
cursor.execute("""
    DROP TABLE IF EXISTS nz_strat_names;
""")
cursor.close()

cursor = connection.cursor()
cursor.execute("""
    DROP TABLE IF EXISTS nz_strat_tree;
""")
cursor.close()

# Prep output tables
cursor = connection.cursor()
cursor.execute("""
    CREATE TABLE nz_strat_names (
       orig_id int(11) NOT NULL,
       name varchar(255) NOT NULL,
       name_usage varchar(255) DEFAULT NULL,
       type varchar(150) DEFAULT NULL,
       area text DEFAULT NULL,
       comments text DEFAULT NULL,
       age text DEFAULT NULL,
       see_also text DEFAULT NULL,
       refs text DEFAULT NULL,
       PRIMARY KEY (orig_id)
    ) ENGINE=MyISAM DEFAULT CHARSET=latin1;

    CREATE TABLE nz_strat_tree LIKE strat_tree;
""")
cursor.close()

cursor = connection.cursor()

# Assumes you have run step #0...
end = max([int(file.replace(".html", "")) for file in os.listdir("html") if file.endswith(".html")]) + 1

for x in xrange(1, end):
    try:
        doc = open("html/" + str(x) + ".html", "r")
    except:
        continue

    soup = BeautifulSoup(doc, "lxml")
    rows = soup.find_all("tr")

    good_data = []
    for row in rows:
        row_data = []
        found = False
        for each in row.find_all("td"):
            if each.has_attr("class"):
                row_data.append(each)
                found = True

        if found:
            good_data.append(row_data)

    # This will store the resultant data for the current name being parsed
    current_name = new_name()

    # Need to parse out ranks!
    for row in good_data:
        # Join everything together for ease of parsing
        content = ' '.join([tag.text for tag in row])

        if "Accession" in content:
            current_name["orig_id"] = clean(row[1].text)

        # Clean () and [] out of name
        elif "Unit name:" in content:
            name = get_name(row[1])
            current_name["name"] = name["name"]
            current_name["usage"] = name["usage"]

        elif "Alternative names" in content:
            d = get_links(row[1])
            for each in d:
                insert_hierarchy(each["id"], "synonym", current_name["orig_id"])

        elif "Part of:" in content:
            d = get_links(row[1])
            for each in d:
                insert_hierarchy(each["id"], "parent", current_name["orig_id"])

        elif "Unit type:" in content:
            current_name["type"] = clean(row[1].text)

        elif "Geographic area:" in content:
            current_name["area"] = get_areas(row[1])

        elif "Compiler comments:" in content:
            current_name["comments"] = clean(row[1].text)

        elif "Age:" in content:
            current_name["age"] = clean(row[1].text)

        elif "See also" in content:
            refs = get_refs(row)
            # Produces pipe-delimited references, with the URL (if applicable) * delimited
            current_name["see_also"] = "|".join(["*".join([ref[key] for key in ref if len(ref[key])]) for ref in refs])

        elif "References" in content:
            refs = get_refs(row)
            # Produces pipe-delimited references, with the URL (if applicable) * delimited
            current_name["refs"] = "|".join(["*".join([ref[key] for key in ref if len(ref[key])]) for ref in refs])

    print json.dumps(current_name, indent=2)

    # Toss it into MariaDB
    cursor.execute("""
        INSERT INTO nz_strat_names (orig_id, name, name_usage, type, area, comments, age, see_also, refs) VALUES (%(orig_id)s, %(name)s, %(usage)s, %(type)s, %(area)s, %(comments)s, %(age)s, %(see_also)s, %(refs)s)
    """, current_name)
