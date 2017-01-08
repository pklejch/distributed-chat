# MI-DSV semestrální práce
Cílem této semestrální práce bylo vytvořit distribuovaný symetrický program implementující chat, 
který bude využívat volby vůdce (algoritmus Chang-Roberts) k úplnému uspořádání zpráv v systému.

Program je napsán v jazyce Python ve verzi 3, není kompatibilní s Pythonem verze 2. 
Program používá většinou standardní moduly, pro zpracování příkazové řádky používá modul click.

## Jak to funguje
Při startu programu se skrz parametry programu předá informace o IP adrese a portu, na kterém bude uzel poslouchat.
Dále se uvede informace o IP adrese a portu, kam se bude uzel připojovat. 
Pokud tato informace není specifikována, uzel se připojí sám k sobě. 
Tímto způsoběm se inicializuje první uzel.

### Přidání uzlu do systému
Další připojované uzly se uspořádávají do virtuálního jednosměrného kruhu. 
Tato situace by se dala popsat takto. Mějme dva navzájem propojené uzly A a B (A->B, B->A). 
Uzel C kontaktuje uzel A, že se chce připojit do kruhu. 
Uzel A tedy sdělí uzlu C informace o svém následníkovi, uzel A si sám nastaví svého následníka jako uzel C. 
Uzel C na základě informací obdržených od uzlu A si nastaví svého následníka na uzel B. 
Pro uzel B se následník nemění. 
Situace tedy po dokončení připojení vypadá následovně: A->C, C->B, B->A.

### Odebrání uzlu ze systému
Pokud se uzel A rozhodl, že se chce odhlásit ze systému, zašle zprávu CLOSE svému následníkovi (uzel C).
Tato zpráva je propagována dokud nedojde k uzlu (uzel B), který má uzel A jako svého následníka.
Zpráva obsahuje informace o uzlu, který byl následník uzlu A (tedy informace o uzlu C). 
Uzel B si tedy upraví svého následníka jako uzel C. Uzel B následně pošle zprávu uzlu A, že je možné bezpečně ukončit činnost.

### Neočekávaný pád uzlu
V systému jsou posílány průběžné zpávy PING. Každý uzel kontroluje, zdali uzel za ním poslal zprávu PING.
Tyto zprávy se posílají každé dvě sekundy.
Pokud uzel neobdrží zprávu PING 3x po sobě (uzel A), je uzel za ním ohlášen za mrtvý (uzel B).
Uzel (uzel A) následně pošle zprávu WHO_IS_DEAD, který obsahuje informace o tomto uzlu (o uzlu A).
Tato zpráva je v kruhu postupně předávána, dokud zpráva nedorazí k uzlu, který zprávu nemůže doručit dál (uzel C). 
Tento uzel (uzel C) si tedy nastaví svého následníka dle informací ze zprávy na uzel A.

### Posílání textových zpráv v systému
Pokud uzel pošle textovou zprávu jinému uzlu, je tato zpráva nejprve přeposílána dále, dokud nedorazí k vůdci.
Vůdce označí tuto zprávu a následně je tato zpráva přeposílána dokud nedorazí k příjemci. Příjemce si zprávu poté zobrazí.

## Uzel

Každý uzel s skládá z několika částí:
  - Server
  - Klient
  - Pinger
  - Fronta zpráv
  - Fronta PING zpráv

Sám uzel je identifikován pomocí HASH, který je vytvořena z řetězce (IP:PORT). 
Uzel dále může mít přezdívku, která slouží např. pro snazší posílání textových zpráv v systému.

### Server
Uzel při startu inicializuje server a nechá ho poslouchat na zadaném rozhraní. Tento server je spuštěn v samostatném vlákně.
Server při přijetí každé zprávy vytvoří vlákno, které spustí obslužnou funkci.
Tato funkce na základě typu zprávy rozhodne, kam bude zpráva umístěna.

  - Pokud je to zpráva typu DIE, vlákno skončí činnost.
  - Pokud je to zpráva typu PING, je tato zpráva umístěna do fronty PING zpráv.
  - Pokud je to zpráva jiného typu, je tato zpráva umístěna do běžné fronty zpráv.

### Klient
Klient je inicializován hned po serveru a v nekonečné smyčce vybírá zprávy z fronty zpráv.
Vybraná zpráva z fronty je zpracována v obslužné funkci.
Na základě typu zprávy a vnitřního stavu uzlu se rozhodne co se bude dělat 
a jestli klient pošle nějakou zprávu svému následníkovi.

### Pinger
Tato část uzlu vybírá PING zprávy z fronty PING zpráv a kontroluje zdali se předchůdce neopozdil s PING zprávami.
Pokud přechůdce neposlal PING zprávu v časovém limitu, je zahájena akce na obnovení virtuálního kruhu (viz výše).

## Chang-Roberts algoritmus
Tento algoritmus je spuštěn při třech událostech:

  - Nový uzel se připojil do systému.
  - Uzel se odpojil ze systému.
  - Uzel neočekávaně umřel.

## Jak nainstalovat a spustit
1. Rozbalit archiv.
2. Přesunout se do rozbaleného archivu.
3. Vytvořit virtuální prostředí pro Python. ```python3 -m venv env```
4. Aktivovat virtuální prostředí. ```. env/bin/activate```
5. Nainstalovat závislosti. ```python -m pip install -r requirements.txt```
6. Spustit pomocí: ```python -m distributed-chat cli IP:PORT [-i IPcíle:PORTcíle]```


