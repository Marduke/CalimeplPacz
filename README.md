# CalimeplPacz

Calibre metadata plugin Pack Czech

Repository for all great and quality Czech sources of metadata for Calibre

# Pro Èechy

Metadata pluginy pro èeské zdroje pro Calibre


P.S.: píšu znova plugin pro Databazeknih.cz, protože ten pùvodní blbne a navíc neumí co by mohl, a píšu ho s jiným identifikátorem, protože pro plnou funkènost je potøeba mìnit styl generování id

#Pokud Vám chybí plugin pro nìkterou stánku nebo Vám nìco nefuguje pište do issues nebo na mail marduke@centrum.cz

# Práce na pluginech
V roce 2013 jsem sice nìjaký plugin napsal, ale bylo to hodnì narychlo a výsledek se mi po mìsícíh používání moc nezamlouval.
U ostatních pluginù to také nebyla žádná sláva takže se rozhodl to všechno zahodit a psat poøádnì a na zelené louce.
Každopádnì chci, aby každý plugin stahoval co možná nejvíc dat a aby byl rozumnì konfigurovatelný
Až budu se svojí prací spokojen tak ji pošlu a se stane souèástí Calibre

##Struktura
Každý adresáø pøedstavuje jeden plugin
Je možno sputit jeho test pøes run.bat
Jelikož píšu v Pydev tak mi pøi více souborech v pluginu hlásí prostøedí neznámé tøídy. To jsem vyøešil buildovacím scriptem. Takže NELZE vzít obsah vybraného adresáøe a zabalit jako Calibre plugin. Musí se spustit build.py/buidl.bat podobnì jak je to v run.bat a poté teplve zabalit. Pluginy také obsahují pomocnou tøídu na výpisy stažených dat Devel. Ta se musí pøidat také.

##Hotovo z minula:
Bookfan.eu

##Plan:
- [x] Databazeknih.cz - 100% v1.0.0
- [x] cbdb.cz - 100% v1.0.0
- [ ] legie.cz - 0%
- [ ] baila.cz - 0%
- [ ] kdb.cz - 0%
- [ ] leganto.cz - 0%
- [ ] onlineknihovna.cz - 0%
- [ ] knihi.cz - 0%
- [ ] pitaval.cz - 0%

pozn.: 90% => chybí configurace

##Detailní funkènost
### Vše
- titul
- autoøi
- kategorie == tagy
- obalka
- serie vè. indexu

### Databazeknih
- obálka 100x166 - 100x171
- série
- rozlišení povídky od knihy, pokud je detekována povídka je pøidán tag Povídka
- tagy serveru(neplést s kategoriemi, server to rozlišuje) se pøidávají do tagù knihy ke kategoriím
- výpis povídek a tag Sbírka povídek pokud se jedná o povídkovou sbírku
- výpis knih ve kterých se kniha nachází pokud se jedná o povídku
- rok vydání a prvního vydání
- edice se pøidává mezitagy

### Cbdb
- obálka cca 141x210 a obèas vìtší
- pokud je více obálek vrací dle max_cover option, výchozí hodnota je 5 
- série index je nespolehlivý, je udáván pouze seøezený seznam knih v sérii
