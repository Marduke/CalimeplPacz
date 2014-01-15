# CalimeplPacz

Calibre metadata plugin Pack Czech

Repository for all great and quality Czech sources of metadata for Calibre

# Pro Èechy

Metadata pluginy pro èeské zdroje pro Calibre


P.S.: píšu znova plugin pro Databazeknih.cz, protoe ten pùvodní blbne a navíc neumí co by mohl, a píšu ho s jinım identifikátorem, protoe pro plnou funkènost je potøeba mìnit styl generování id

#Pokud Vám chybí plugin pro nìkterou stánku nebo Vám nìco nefuguje pište do issues nebo na mail marduke@centrum.cz

# Práce na pluginech
V roce 2013 jsem sice nìjakı plugin napsal, ale bylo to hodnì narychlo a vısledek se mi po mìsícíh pouívání moc nezamlouval.
U ostatních pluginù to také nebyla ádná sláva take se rozhodl to všechno zahodit a psat poøádnì a na zelené louce.
Kadopádnì chci, aby kadı plugin stahoval co moná nejvíc dat a aby byl rozumnì konfigurovatelnı
A budu se svojí prací spokojen tak ji pošlu a se stane souèástí Calibre

##Struktura
Kadı adresáø pøedstavuje jeden plugin
Je mono sputit jeho test pøes run.bat
Jeliko píšu v Pydev tak mi pøi více souborech v pluginu hlásí prostøedí neznámé tøídy. To jsem vyøešil buildovacím scriptem. Take NELZE vzít obsah vybraného adresáøe a zabalit jako Calibre plugin. Musí se spustit build.py/buidl.bat podobnì jak je to v run.bat a poté teplve zabalit. Pluginy také obsahují pomocnou tøídu na vıpisy staenıch dat Devel. Ta se musí pøidat také.

##Hotovo z minula:
Bookfan.eu

##Plan:
- [x] Databazeknih.cz - 90% - chybi configurace
- [ ] cbdb.cz - 5%
- [ ] legie.cz - 0%
- [ ] baila.cz - 0%
- [ ] kdb.cz - 0%
- [ ] leganto.cz - 0%
- [ ] onlineknihovna.cz - 0%
- [ ] knihi.cz - 0%
- [ ] pitaval.cz - 0%

##Detailní funkènost
### Vše
- titul
- autoøi
- kategorie == tagy

### Databazeknih
- obalka (pouze 100x166 - 100x171)
- série
- rozlišení povídky od knihy, pokud je detekována povídka je pøidán tag Povídka
- tagy serveru(neplést s kategoriemi, server to rozlišuje) se pøidávají do tagù knihy ke kategoriím
- vıpis povídek a tag Sbírka povídek pokud se jedná o povídkovou sbírku
- vıpis knih ve kterıch se kniha nachází pokud se jedná o povídku
- rok vydání a prvního vydání
- edice se pøidává mezitagy