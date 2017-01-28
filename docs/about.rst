About distributed-chat
======================
This program implements distributed chat without need of a central server.
The main goal of this program is to demonstrate how to achieve full ordering of messages in distributed system,
 using central authority.
The distributed system will automatically elect one node as a leader (using Chang-Roberts algorithm).
The leader is now a central authority of this distributed system.
All messages are now pass through leader.
If leader leaves the distributed system (or dies unexpectedly), new leader will be automatically chosen.
