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

##Detailn� funk�nost
### V�e
- titul
- auto�i
- kategorie == tagy

### Databazeknih
- obalka (pouze 100x166 - 100x171)
- s�rie
- rozli�en� pov�dky od knihy, pokud je detekov�na pov�dka je p�id�n tag Pov�dka
- tagy serveru(nepl�st s kategoriemi, server to rozli�uje) se p�id�vaj� do tag� knihy ke kategori�m
- v�pis pov�dek a tag Sb�rka pov�dek pokud se jedn� o pov�dkovou sb�rku
- v�pis knih ve kter�ch se kniha nach�z� pokud se jedn� o pov�dku
- rok vyd�n� a prvn�ho vyd�n�
- edice se p�id�v� mezitagy