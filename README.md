# CalimeplPacz

Calibre metadata plugin Pack Czech

Repository for all great and quality Czech sources of metadata for Calibre

# Pro �echy

Metadata pluginy pro �esk� zdroje pro Calibre


P.S.: p�u znova plugin pro Databazeknih.cz, proto�e ten p�vodn� blbne a nav�c neum� co by mohl, a p�u ho s jin�m identifik�torem, proto�e pro plnou funk�nost je pot�eba m�nit styl generov�n� id

#Pokud V�m chyb� plugin pro n�kterou st�nku nebo V�m n�co nefuguje pi�te do issues nebo na mail marduke@centrum.cz

# Pr�ce na pluginech
V roce 2013 jsem sice n�jak� plugin napsal, ale bylo to hodn� narychlo a v�sledek se mi po m�s�c�h pou��v�n� moc nezamlouval.
U ostatn�ch plugin� to tak� nebyla ��dn� sl�va tak�e se rozhodl to v�echno zahodit a psat po��dn� a na zelen� louce.
Ka�dop�dn� chci, aby ka�d� plugin stahoval co mo�n� nejv�c dat a aby byl rozumn� konfigurovateln�
A� budu se svoj� prac� spokojen tak ji po�lu a� se stane sou��st� Calibre

##Struktura
Ka�d� adres�� p�edstavuje jeden plugin
Je mo�no sputit jeho test p�es run.bat
Jeliko� p�u v Pydev tak mi p�i v�ce souborech v pluginu hl�s� prost�ed� nezn�m� t��dy. To jsem vy�e�il buildovac�m scriptem. Tak�e NELZE vz�t obsah vybran�ho adres��e a zabalit jako Calibre plugin. Mus� se spustit build.py/buidl.bat podobn� jak je to v run.bat a pot� teplve zabalit. Pluginy tak� obsahuj� pomocnou t��du na v�pisy sta�en�ch dat Devel. Ta se mus� p�idat tak�.

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

##Detailn� funk�nost
### V�e
- titul
- auto�i
- kategorie == tagy
- obalka
- serie v�. indexu
- nakladatel
- rok vyd�n�
- hodnocen� (1-5 hv�zdi�ek)
- i ka�d�ho pluginu je mo�no vybrat max_search, ozna�uje kolik detail� knihy se m� detailn� zpracovat, pokud jich v�bec tolik najde, pokud jich bude v�c se�ad� je podle p�ibli�n� relevance (odpov�daj�c� jm�no a auto�i) a vezme pouze tolik kolik ur�� parametr
- pokud je v�ce ob�lek vrac� dle max_cover option

### Databazeknih
- cca 182 000 knih
- ob�lka 100x166 - 100x171
- rozli�en� pov�dky od knihy, pokud je detekov�na pov�dka je p�id�n tag Pov�dka
- tagy serveru(nepl�st s kategoriemi, server to rozli�uje) se p�id�vaj� do tag� knihy ke kategori�m
- v�pis pov�dek a tag Sb�rka pov�dek pokud se jedn� o pov�dkovou sb�rku
- v�pis knih ve kter�ch se kniha nach�z� pokud se jedn� o pov�dku
- rok vyd�n� a prvn�ho vyd�n�
- edice se p�id�v� mezitagy

### Cbdb
- cca 91 500 knih
- v�ce ob�lek o velikosti 141x210 a ob�as v�t��
- s�rie index je nespolehliv�, je ud�v�n pouze se�ezen� seznam knih v s�rii

### Onlineknihovna
- cca 1 300 knih
- ob�lky 477x756 a v�t��

### Legie
- datab�ze knih Fantasy a Sci-Fi
- cca 14 500 knih a 21500 pov�dek
- v�ce ob�lek, 150x230
- s�rie v�etn� neza�azen�ch knih
- informace o sv�t� knihy, mo�no zapnout/vypnout a definovat prefix sv�ta
- detailn� v�pis ocen�n� knihy

### Kdb
- cca 60 000 knih
- v�ce ob�lek r�zn� velikosti, jpg i gif

### Pitaval
- datab�ze detektivn�, thrillerov� a �pion�n� literatury
- cca 11 300 knih a 5600 pov�dek

### Baila
- cca 1 200 000 knih v�ech kategori�
- ob�lka 140-160x225
- mnoho tag�

### Knihi
- cca 48 000 knih
- obr�zky 40x61 - ignorov�ny

# Download
3.12.2014 - http://uloz.to/xGCPPJxF/plugins-zip