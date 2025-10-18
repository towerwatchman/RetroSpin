#include "update_db.h"
#include <tinyxml2.h>
#include <sqlite3.h>
#include <iostream>

void updateDatabase() {
    system("wget http://redump.org/datfile/psx/ -O /tmp/psx.dat");

    tinyxml2::XMLDocument doc;
    if (doc.LoadFile("/tmp/psx.dat") != tinyxml2::XML_SUCCESS) {
        std::cerr << "Failed to load DAT" << std::endl;
        return;
    }

    sqlite3* db;
    sqlite3_open(DB_PATH.c_str(), &db);
    sqlite3_exec(db, "CREATE TABLE IF NOT EXISTS games (serial VARCHAR PRIMARY KEY, title VARCHAR);", NULL, NULL, NULL);
    sqlite3_exec(db, "DELETE FROM games;", NULL, NULL, NULL); // Clear old

    auto root = doc.FirstChildElement("datafile");
    for (auto game = root->FirstChildElement("game"); game; game = game->NextSiblingElement("game")) {
        std::string title = game->Attribute("name");
        std::string serial = game->FirstChildElement("serial")->GetText();
        std::string sql = "INSERT OR REPLACE INTO games (serial, title) VALUES ('" + serial + "', '" + title + "');";
        sqlite3_exec(db, sql.c_str(), NULL, NULL, NULL);
    }

    sqlite3_close(db);
}