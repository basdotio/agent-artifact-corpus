local url = "http://localhost:8080"
task.spawn(function()
    while task.wait() do
        local res = request({Url = url.."/task", Method = "GET"})
        if res and res.Body and res.Body ~= "" then
            local f, err = loadstring(res.Body)
            local out = ""
            if f then
                local success, r = pcall(f)
                out = success and tostring(r) or "Error: "..tostring(r)
            else
                out = "Syntax Error: "..tostring(err)
            end
            request({Url = url.."/result", Method = "POST", Body = out})
        end
    end
end)
