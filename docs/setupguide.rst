How to install and run
----------------------

1. Rozbalit archiv.
2. Přesunout se do rozbaleného archivu.
3. Vytvořit virtuální prostředí pro Python. ``python3 -m venv env``
4. Aktivovat virtuální prostředí. ``. env/bin/activate``
5. Nainstalovat závislosti.
   ``python -m pip install -r requirements.txt``
6. Spustit pomocí:
   ``python -m distributed-chat cli -vv IP:PORT [-i IPcíle:PORTcíle]``
