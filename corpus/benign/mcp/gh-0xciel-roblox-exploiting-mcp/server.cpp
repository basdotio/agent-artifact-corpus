#include <httplib.h>
#include <string>
#include <mutex>
#include <condition_variable>
std::string code = "";
std::string result = "";
bool has_task = false;
bool has_result = false;
std::mutex m;
std::condition_variable cv;
int main() {
    httplib::Server s;
    s.Post("/execute", [](const auto& req, auto& res) {
        std::unique_lock<std::mutex> l(m);
        code = req.body;
        has_task = true;
        has_result = false;
        cv.wait(l, [] { return has_result; });
        res.set_content(result, "text/plain");
        });
    s.Get("/task", [](const auto& req, auto& res) {
        std::lock_guard<std::mutex> l(m);
        if (has_task) {
            res.set_content(code, "text/plain");
            has_task = false;
        }
        });
    s.Post("/result", [](const auto& req, auto& res) {
        std::lock_guard<std::mutex> l(m);
        result = req.body;
        has_result = true;
        cv.notify_one(); 
        });
    s.listen("localhost", 8080);
}
