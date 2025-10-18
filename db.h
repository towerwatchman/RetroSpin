#ifndef DB_H
#define DB_H

#include <map>
std::string getGameTitle(const std::string& serial);
std::map<std::string, std::string> getGameData(const std::string& serial);

#endif