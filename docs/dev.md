# Challenges

* The application is able to run as a Tab UI and stay active indefinitely.
    - This means no active thread can be used. The application can only wait
      idle till triggered by user interactions.
    - Solution: command execution is directly invoked by TextView delegate.
      No active reading thread for main level user inputs (unlike running
      scripts which have an active reading thread to wait for user data).

* The ObjC calls are slow especially for large text building and rendering
    - It is very inefficient if we simply rebuild and replace the entire text
      buffer for every text changes.
    - Solution: sequential editing.


# Design
