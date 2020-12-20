Packages required for this program:

- flask
- requests
- json
- math

This program is using the flask framework to launch web services, by running **python fsrch.py**, the website will be launched at http://127.0.0.1:5000/, the user will be reuqired to type in three values: **favor**, **location** and **number of displays**. The user can click the search button, the page will be redirected to the **search_items** , this page will show all the seach results in the format of cards. There are also buttons called **Show more**, users can click these buttons to view some comments from previous customers. The data will be stored in the cache for the next search.

The search data will be stored in the sqlite database, by cliking the History button in the navbar, the history of searching can be displayed in the history view.