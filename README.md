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
Bookfan.eu - stanka mela dlouho vypadky nebo aspon problemy s obrazky, dnes je z ni inzerentni rozcestnik :-(((

##Plan:
- [x] Databazeknih.cz - v1.0.0
- [x] cbdb.cz - v1.0.2
- [x] onlineknihovna.cz - v1.0.0
- [x] legie.cz - v1.0.1
- [x] kdb.cz - v1.0.1
- [x] pitaval.cz - v1.0.0
- [x] baila.cz - v1.0.0
- [x] palmknihy - v1.0.0

##Detailní funkènost
### Vše
- titul
- autoøi
- kategorie == tagy
- obalka
- serie vè. indexu
- nakladatel
- rok vydání
- hodnocení (1-5 hvìzdièek)
- i kadého pluginu je mono vybrat max_search, oznaèuje kolik detailù knihy se má detailnì zpracovat, pokud jich vùbec tolik najde, pokud jich bude víc seøadí je podle pøibliné relevance (odpovídající jméno a autoøi) a vezme pouze tolik kolik urèí parametr
- pokud je více obálek vrací dle max_cover option

### Databazeknih
- cca 182 000 knih
- obálka 100x166 - 100x171
- rozlišení povídky od knihy, pokud je detekována povídka je pøidán tag Povídka
- tagy serveru(neplést s kategoriemi, server to rozlišuje) se pøidávají do tagù knihy ke kategoriím
- vıpis povídek a tag Sbírka povídek pokud se jedná o povídkovou sbírku
- vıpis knih ve kterıch se kniha nachází pokud se jedná o povídku
- rok vydání a prvního vydání
- edice se pøidává mezitagy

### Cbdb
- cca 91 500 knih
- více obálek o velikosti 141x210 a obèas vìtší
- série index je nespolehlivı, je udáván pouze seøezenı seznam knih v sérii

### Onlineknihovna
- cca 1 300 knih
- obálky 477x756 a vìtší

### Legie
- databáze knih Fantasy a Sci-Fi
- cca 14 500 knih a 21500 povídek
- více obálek, 150x230
- série vèetnì nezaøazenıch knih
- informace o svìtì knihy, mono zapnout/vypnout a definovat prefix svìta
- detailní vıpis ocenìní knihy

### Kdb
- cca 60 000 knih
- více obálek rùzné velikosti, jpg i gif

### Pitaval
- databáze detektivní, thrillerové a špionání literatury
- cca 11 300 knih a 5600 povídek

### Baila
- cca 1 200 000 knih všech kategorií
- obálka 140-160x225
- mnoho tagù

### Knihi
- cca 48 000 knih
- obrázky 40x61 - ignorovány

# Download
3.12.2014 - http://uloz.to/xGCPPJxF/plugins-zip