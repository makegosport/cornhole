Software
========

The software for the Cornhole game is built with seperate services that inter-connect via `MQTT
<https://mqtt.org/>`_ (This is light-weight protocol for IoT devices to interact). The main
component is a MQTT Broker, services can publish topics to the broker and other servces can
subscribe to those topics.

.. graphviz::

   digraph foo {
     broker [label="MQTT Broker"];
     game [label="Game"];
     twitter_bot [label="Twitter Bot"];
     broker -> game;
     broker -> twitter_bot;
   }


Main Game
---------

The main game aggregates the MQTT topics from the board and controls the lights. It also keeps the
score during a games.

.. automodule:: game.make_game
    :members:


