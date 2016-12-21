# distributed-chat
This program will implement distributed chat on virtual ring topology network.
Furthermore this program will implement Chang-Roberts algorithm to achieve full ordering of messages.

Features:
  - Nodes can freely join into existing ring, based on information about one node (IP:port). First node will join with itself into ring.
  - Ring will recover from unexpected disconnect of one node at the time.
  - One node will be elected as central authority (leader), all messages will be then passed through leader.
  - Leader will be elected using Chang-Roberts algorithm.
  - GUI in Qt, it will also have CLI.
  - Encryption of messages.
  

