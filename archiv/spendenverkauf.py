# -*- coding: utf-8 -*-
"""
Created on Thu May 28 20:51:22 2020

With this script I created an HTML file that displayed 
all items that we had for sale in our flea-market


@author: Simon
"""
import json
from fenster_bildschirm import get_leihlokaldata
from leihlokal import Store

with open('settings.json', 'r', encoding='latin1') as f:
    settings = json.load(f)
excel_file = settings['leihgegenstaendeliste']
print('Lade Datenbank...')
store = Store.parse_file(excel_file)


#%%

for_sale = ['2703', '2716','500','702', '3302', '204', '501', '3304', '614', '1321', '2403', '2402', '3016', '1606', '2608', '1712', '2706', '310', '611', '105', '1508', '602', '2916', '409', '3311', '1809', '303', '2108', '914', '1729', '1517', '3210', '1413', '3215', '3216', '21', '411', '6115', '2307', '1106', '2305', '5015', '402', '825', '1428', '1306', '304', '803', '1222', '320', '1105', '3221', '1108', '2504', '3208', '2818', '608', '112', '1303', '1103', '812', '17', '3008', '2603', '822', '2604', '1101', '612', '610', '16', '1301', '1223', '2513', '6003', '425', '1611', '1611', '3203', '212', '1415', '3010', '1208', '2406', '3102', '1808', '3310', '1614', '1117', '1205', '406', '2103', '1603', '19', '4', '309', '3212', '2909', '2518', 'ohne', '518', '716', '325', '2905', '1513', '1325', '1211', '609', '1012', '427', '427', '1501', '2520', '6111', '2511', '1204', '1317', '3', '113', '3207', '3206', '1411', '1209', '2523', '1622', '2704', '1206', '1916', '1309', '1914', '3015', '100', '506', '1113', '1113', '1113', '2514', '2315', '1203', '1008', '519', '507', '924', '1318', 'ohne', '1104', '2316', '2707', '14', '1005', '923', '513', '1212', '3001', '2209', '1327', '1307', '1604']
sold = ['2403',
        '2315','1222','3016','2518','2716',
        '3207', '2703', '2604', '2511', '611',
        '3210', '2706', '1113', '1321', '702', '1729', '2209',
        '924', '3015', '2112', '1005', '1106', '1327', '1916',
        '2704','1325', '310', '602', '2315',
        '100', '914', '1008', '1204', '1013', '1603', '1604', '1209', '2402', '1910', '2513', '1109', '2209',
        '1914','1101', '104', '827', '1104', '1309', '1428', '1508', '1611', '1622', '2103', '2523', '2909', '3208',
        '1808','2307','406','3311','2905','2608','2603','2520','1614','1606','1303','506','105','2305','3102','1208', '2406','2406',
        '5015', '1206','2514','2520' ,'325', '3215', '825','3220','1402', '309','1301', '402', '2316', '2705', '1902','824', '1214', '1413', '3302', '716', '17']

for_sale = set(for_sale)
names, codes, hrefurls, images_urls = get_leihlokaldata()

img_urls = {int(code):url for code, url in zip(codes, images_urls)}
urls = {int(code):url for code, url in zip(codes, hrefurls)}
#%%


head = """<html class="no-js"  lang="de-DE">

	<head>
		<meta charset="utf-8">"""
css = """<style>
.description {
    font-family: "Arial";
    text-align: center;
}

.text {
    font-family: "Arial";
    text-align: left;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  /* This is better for small screens, once min() is better supported */
  /* grid-template-columns: repeat(auto-fill, minmax(min(200px, 100%), 1fr)); */
  grid-gap: 1rem;
  /* This is the standardized property now, but has slightly less support */
  /* gap: 1rem */
}

.img {
   width: 100%;
   position: relative;
   font-weight: bold;
   font-family: "Arial";
   background-color: white;
}

.img-sold {
    -webkit-filter: opacity(.5) blur(2px);
    filter: opacity(.3) blur(3px);
}


</style>

"""

items = [store.items.get(int(id)) for id in for_sale if (id.strip().isdigit() and store.items.get(int(id)) is not None)]

for item in items:
    item.url = urls.get(item.item_id, 'https://www.buergerstiftung-karlsruhe.de/404')
    item.img = img_urls.get(item.item_id, 'https://www.buergerstiftung-karlsruhe.de/notfound.png')

categories = ['Küche','Freizeit', 'Haushalt', 'Heimwerker', 'Kinder', 'Garten']

body = '<h1 class="text"><u><b>Spendenverkauf im <b>leih<font color="red">.</font>lokal</b></u></b></h1>\n'
body += """<div style="width:700px;">
<p class="text"><b>Unser Lager platzt aus allen Nähten!</b><br>
Deshalb haben wir entschieden uns von einigen Artikeln zu trennen die wir doppelt und dreifach haben.
Ebenso haben wir einige obskure Artikel aussortiert, die noch nie geliehen wurden, bzw. welche für eine kurze Leihdauer nicht sinnvoll erscheinen.<br>
<br>
Diese Artikel sind ab sofort zur Besichtigung im <b>leih<font color="red">.</font>lokal</b> ausgestellt und können gegen einen frei wählbaren <b>Spendenbetrag</b> mitgenommen werden. Wie ihr wisst, decken wir unsere laufenden Kosten vorwiegend über Spenden, welche während der fünf Wochen durch die abgesagten Konzerte und die Covid-19 Schliessung ausblieben. Diese finanzielle Lücke möchten wir durch diese Aktion zumindest ein Stückchen schließen<br><br>
Hier findet ihr eine Liste aller Artikel von denen wir uns trennen. 
<br><br>
<u>Übersicht</u>:</p><blockquote><p class="text">
"""

body += '<br>'.join(f'<a href="#{cat}">   {i+1}. {cat}</a>' for i,cat in enumerate(categories))
body += '</p></blockquote></div>'
for category in categories:
    items_category = [item for item in items if item.category==category]
    body += f'\n<br><br>\n<h1 class="text" id="{category}">{category}</h2>'
    # body += f'<small class="text">Die Liste wird nicht live aktualisiert. Wenn ihr auf einen Gegenstand klickt und er nicht mehr auf unserer Webseite ist, wurde er schon verkauft.<br></small>'
    body += '\n<br><div class="grid">\n'
    for item in items_category:
        # if item.img is None: continue
        if str(item.item_id) in sold: continue
        imgclass = 'img-sold' if str(item.item_id) in sold else 'img'
        
        div= f"""
    <div class="item">
        <div class="img">
            <a href="{item.url}" class="{imgclass}"> <img src="{item.img}" class="img" border="1"></a>
            {'<div style="bottom: 50%; position: absolute; left: 27%;font-size: x-large;"><larger>schon weg</larger></div>' if imgclass=='img-sold' else ''}
        </div>
        <div class="description">
            <p class="description"><b>{item.item_name}</b> ({item.item_id})<br> {item.properties}</p>
        </div>
    </div>
        """
        body += div
    body += '</div>'

body += '</div>'    

 
with open('c:/users/simon/desktop/spendenverkauf.html', 'w') as f:
    f.write(head + css + body)