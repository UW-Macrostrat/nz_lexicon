import urllib2
from bs4 import BeautifulSoup
import time
import os

# Figure out where to start scraping
files = [int(file.replace(".html", "")) for file in os.listdir("html") if file.endswith(".html")]

if len(files):
    start = max(files)
else :
    start = 1

for x in xrange(start, 7400):

  # Be kind, don't thrash
  time.sleep(10)

  print x

  req = urllib2.urlopen("http://data.gns.cri.nz/stratlex/view.jsp?id=" + str(x))

  # Soup it
  soup = BeautifulSoup(req.read(), "lxml")

  # Check if any data was returned
  if soup.find("table", class_="internal").tr.td.text != "No data found for that id":
      with open("html/" + str(x) + ".html", "w") as out:
          # Write only what we need to a file
          out.write(BeautifulSoup(unicode.join(u'\n',map(unicode, soup.find("table", class_="internal").find_all("tr"))), "lxml").prettify().encode('UTF-8'))
