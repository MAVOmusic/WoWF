-- ForeverCompanion / Core.lua
-- State, saved variables, plan logic and slash commands.
-- UI lives in UI.lua and is optional: everything here works headless.
--
-- Defensive by design: the Midnight client (Interface 16001) can hand back
-- "secret" values from unit APIs, and a single unguarded comparison inside an
-- event handler would abort silently. Every risky call is wrapped, and the event
-- handler always reports what went wrong instead of dying quietly.

local PREFIX = "|cff33ff99Forever|r|cffffd200Companion|r: "

ForeverCompanion = ForeverCompanion or {}
local FC = ForeverCompanion

FC.version = "0.1.1"
FC.frame = nil
FC.tab = "next"
FC.lastError = nil

local Data = ForeverCompanionData

local function Print(msg)
	if DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.AddMessage then
		DEFAULT_CHAT_FRAME:AddMessage(PREFIX .. tostring(msg))
	else
		print(PREFIX .. tostring(msg))
	end
end
FC.Print = Print

local function Config(msg)
	if DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.AddMessage then
		DEFAULT_CHAT_FRAME:AddMessage(PREFIX .. "|cffffffff" .. tostring(msg) .. "|r")
	end
end
FC.Config = Config

-- A number from a WoW API, or a fallback when the value is missing, nil, or
-- "secret" (secret values raise as soon as you do arithmetic on them).
local function SafeNumber(fn, fallback)
	local ok, value = pcall(fn)
	if not ok then
		return fallback
	end
	if issecretvalue and issecretvalue(value) then
		return fallback
	end
	local okNumber, number = pcall(tonumber, value)
	if okNumber and number then
		return number
	end
	return fallback
end
FC.SafeNumber = SafeNumber

-- ---------------------------------------------------------------- saved vars

local function InitDB()
	if type(ForeverCompanionDB) ~= "table" then
		ForeverCompanionDB = {}
	end
	local db = ForeverCompanionDB
	if type(db.done) ~= "table" then
		db.done = {}
	end
	if db.debug == nil then
		db.debug = false
	end
	if db.everShown == nil then
		db.everShown = false
	end
	-- separate flag from v0.1.0's everShown: 0.1.0 set that at login without ever
	-- showing the panel, so reusing it would suppress the first real open.
	if db.autoOpened == nil then
		db.autoOpened = false
	end
	if db.minimap == nil then
		db.minimap = true
	end
	return db
end
FC.InitDB = InitDB

local function DB()
	return ForeverCompanionDB or InitDB()
end

-- ---------------------------------------------------------------- plan logic

function FC:PlanEntry(key)
	if not Data then return nil end
	for _, entry in ipairs(Data.plan) do
		if entry.key == key then
			return entry
		end
	end
	return nil
end

function FC:IsDone(key)
	local db = DB()
	return db.done[key] and true or false
end

function FC:SetDone(key, value)
	local db = DB()
	if value then
		db.done[key] = true
	else
		db.done[key] = nil
	end
end

function FC:ToggleDone(key)
	local newValue = not self:IsDone(key)
	self:SetDone(key, newValue)
	return newValue
end

-- Unfinished, actionable plan entries, best priority first.
function FC:OpenPlan(maxPriority)
	local out = {}
	if not Data then return out end
	for _, entry in ipairs(Data.plan) do
		local status = entry.status or "open"
		local isSkip = (status == "skipped" or status == "hold")
		local prioOk = (not maxPriority) or (entry.priority or 99) <= maxPriority
		if not isSkip and not self:IsDone(entry.key) and prioOk then
			table.insert(out, entry)
		end
	end
	return out
end

function FC:PlanCounts()
	local done, open, skipped = 0, 0, 0
	if Data then
		for _, entry in ipairs(Data.plan) do
			local status = entry.status or "open"
			if status == "skipped" or status == "hold" then
				skipped = skipped + 1
			elseif self:IsDone(entry.key) then
				done = done + 1
			else
				open = open + 1
			end
		end
	end
	return done, open, skipped
end

-- ---------------------------------------------------------------- level drift

function FC:PlayerLevel()
	local level = SafeNumber(function()
		return UnitLevel and UnitLevel("player")
	end, nil)
	if level and level > 0 then
		return level
	end
	return Data and Data.character.level or nil
end

function FC:StaleLevelBy()
	local snap = Data and Data.character.level
	local now = self:PlayerLevel()
	if not snap or not now then return 0 end
	return now - snap
end

-- Days since the armory snapshot date (UTC, date-only compare).
function FC:SnapshotAgeDays()
	local stamp = Data and Data.snapshotFetchedAt
	if not stamp then return nil end
	local y, m, d = string.match(stamp, "^(%d%d%d%d)%-(%d%d)%-(%d%d)")
	if not y then return nil end
	local thenTime = SafeNumber(function()
		return time({ year = tonumber(y), month = tonumber(m), day = tonumber(d), hour = 12 })
	end, nil)
	local nowTime = SafeNumber(function() return time() end, nil)
	if not thenTime or not nowTime then return nil end
	return math.floor((nowTime - thenTime) / 86400)
end

-- ---------------------------------------------------------------- zone filter

function FC:ZonesForLevel()
	local out = {}
	if not Data then return out end
	local level = self:PlayerLevel() or 1
	for _, zone in ipairs(Data.zones) do
		local lo = zone.levelMin or 1
		local hi = zone.levelMax or 99
		if lo <= level + 5 and hi >= level - 3 then
			table.insert(out, zone)
		end
	end
	return out
end

function FC:SourcesForLevel()
	local out = {}
	if not Data then return out end
	local zones = {}
	for _, zone in ipairs(self:ZonesForLevel()) do
		zones[zone.name] = true
	end
	for _, src in ipairs(Data.sources) do
		if src.zone and zones[src.zone] then
			table.insert(out, src)
		end
	end
	if #out == 0 then
		out = Data.sources
	end
	return out
end

-- ---------------------------------------------------------------- chat views

function FC:ChatStatus()
	if not Data then
		Print("no data loaded (Data.lua missing)")
		return
	end
	local done, open, skipped = self:PlanCounts()
	Config("build " .. tostring(Data.generatedAt)
		.. " · snapshot level " .. tostring(Data.character.level)
		.. " · you are " .. tostring(self:PlayerLevel()))
	Config("plan: " .. open .. " open, " .. done .. " done, " .. skipped .. " parked")
	local age = self:SnapshotAgeDays()
	if age and age > 3 then
		Config("|cffffcc00snapshot is " .. age .. " days old — re-run the armory refresh|r")
	end
end

function FC:ChatPlan(maxPriority)
	local entries = self:OpenPlan(maxPriority or 3)
	if #entries == 0 then
		Print("nothing open — /fw reset clears your tick marks")
		return
	end
	Print("|cffffd200next " .. #entries .. " step(s)|r")
	for index, entry in ipairs(entries) do
		Config(string.format("%d. [P%d] %s → |cff33ff99%s|r  (%s%s)",
			index, entry.priority or 0, entry.label or entry.slot or "?",
			tostring(entry.target), tostring(entry.how),
			entry.zone and (" · " .. entry.zone) or ""))
	end
end

function FC:ChatGear()
	if not Data then
		Print("no data loaded (Data.lua missing)")
		return
	end
	Print("equipment (snapshot)")
	for _, slot in ipairs(Data.equipment) do
		local label = slot.label or slot.slot
		if slot.name then
			Config(string.format("  %-11s |cffffffff%s|r", label, slot.name))
		else
			Config(string.format("  %-11s |cffff5555EMPTY|r", label))
		end
	end
end

function FC:ChatFarm()
	if not Data then
		Print("no data loaded (Data.lua missing)")
		return
	end
	local zones = self:ZonesForLevel()
	if #zones == 0 then
		Print("no zones in the data for this level")
		return
	end
	Print("|cffffd200farming at level " .. tostring(self:PlayerLevel()) .. "|r")
	for _, zone in ipairs(zones) do
		Config(string.format("  %s (%s-%s, %s) — %s",
			tostring(zone.name), tostring(zone.levelMin), tostring(zone.levelMax),
			tostring(zone.faction), tostring(zone.mining)))
	end
end

function FC:ChatProfs()
	if not Data then
		Print("no data loaded (Data.lua missing)")
		return
	end
	Print("professions")
	for _, prof in ipairs(Data.professionPlan) do
		Config(string.format("  %s %s/%s — %s",
			tostring(prof.profession), tostring(prof.current), tostring(prof.cap),
			tostring(prof.action)))
	end
end

-- ---------------------------------------------------------------- diagnostics

local function BuildInfo()
	local version, build, _, interface = GetBuildInfo()
	return tostring(version) .. " / interface " .. tostring(interface or build)
end

function FC:Diag()
	Print("|cffffd200diagnostics|r")
	Config("addon " .. tostring(self.version)
		.. " · " .. tostring(GetAddOnMetadata and GetAddOnMetadata("ForeverCompanion", "Version") or "?")
		.. " · client " .. BuildInfo())
	if Data then
		local done, open, skipped = self:PlanCounts()
		Config("data ok · build " .. tostring(Data.generatedAt)
			.. " · " .. #Data.plan .. " plan rows · " .. #Data.zones .. " zones")
		Config("plan: " .. open .. " open · " .. done .. " done · " .. skipped .. " parked")
		Config("character: " .. tostring(Data.character.name)
			.. " · data level " .. tostring(Data.character.level)
			.. " · live level " .. tostring(self:PlayerLevel()))
	else
		Config("|cffff5555data missing|r — Data.lua did not load")
	end
	if self.frame then
		Config("panel: built · " .. (self.frame:IsShown() and "shown" or "hidden"))
	else
		Config("panel: not built yet (type /fw)")
	end
	Config("minimap button: " .. (self.minimapButton and "yes" or "no")
		.. " · saved position: " .. (DB().position and "yes" or "no"))
	Config("last UI error: " .. (self.lastError and ("|cffff5555" .. tostring(self.lastError) .. "|r") or "none"))
	Config("slash commands: /fw, /forever")
end

-- ---------------------------------------------------------------- slash

local function ResolveEntry(token)
	local entries = FC:OpenPlan()
	if not token or token == "" then
		return nil
	end
	local index = tonumber(token)
	if index and entries[index] then
		return entries[index]
	end
	return FC:PlanEntry(token)
end

local function Help()
	Print("commands")
	Config("/fw — open or close the panel")
	Config("/fw next <1|2|3> — chat view of the plan at that priority or better")
	Config("/fw gear — equipment from the snapshot")
	Config("/fw farm — zones and sources for your level")
	Config("/fw prof — profession next steps")
	Config("/fw done <#> — tick an item off   /fw undo <#>   /fw reset")
	Config("/fw status — data build, plan counts, snapshot age")
	Config("/fw diag — environment dump, useful when something feels broken")
	Config("/fw button — show or hide the minimap button")
	Config("/fw resetpos — put the panel back in the middle")
end

function FC:HandleCommand(message)
	message = tostring(message or "")
	message = message:lower():gsub("^%s+", ""):gsub("%s+$", "")
	local command, rest = string.match(message, "^(%S*)%s*(.*)$")

	if command == "" or command == "show" or command == "toggle" then
		if self.Toggle then
			self:Toggle()
		else
			Print("panel unavailable — use /fw next for the chat view")
		end
	elseif command == "close" or command == "hide" then
		if self.frame then self.frame:Hide() end
	elseif command == "next" or command == "plan" then
		self:ChatPlan(tonumber(rest) or 3)
	elseif command == "gear" then
		self:ChatGear()
	elseif command == "farm" then
		self:ChatFarm()
	elseif command == "prof" or command == "profs" then
		self:ChatProfs()
	elseif command == "status" then
		self:ChatStatus()
	elseif command == "diag" then
		self:Diag()
	elseif command == "resetpos" then
		if self.ResetPosition then
			self:ResetPosition()
		end
		DB().position = nil
		Print("panel position reset")
	elseif command == "button" then
		local db = DB()
		if rest == "on" then
			db.minimap = true
		elseif rest == "off" then
			db.minimap = false
		else
			db.minimap = not db.minimap
		end
		if self.SyncMinimapButton then
			self:SyncMinimapButton()
		end
		Print("minimap button " .. (db.minimap and "on" or "off"))
	elseif command == "done" or command == "undo" then
		local entry = ResolveEntry(rest)
		if not entry then
			Print("pick an entry with /fw next, then /fw " .. command .. " <index>")
			return
		end
		local isDone = (command == "done")
		self:SetDone(entry.key, isDone)
		self:RefreshPanel()
		Print((isDone and "ticked off: " or "reopened: ") .. tostring(entry.target))
	elseif command == "reset" then
		DB().done = {}
		self:RefreshPanel()
		Print("all tick marks cleared")
	else
		Help()
	end
end

function FC:RefreshPanel()
	if self.frame and self.frame.Refresh then
		local ok, err = pcall(self.frame.Refresh, self.frame)
		if not ok then
			self.lastError = tostring(err)
			Print("|cffff5555refresh failed:|r " .. tostring(err))
		end
	end
end

-- ---------------------------------------------------------------- events

local function OnLogin()
	InitDB()
	if not Data then
		Print("|cffff5555Data.lua did not load|r — re-run scripts/build_addon_data.py")
		return
	end
	local _, open = FC:PlanCounts()
	local stale = FC:StaleLevelBy()
	Print("v" .. FC.version .. " loaded · " .. open .. " step(s) open · "
		.. "|cff33ff99/fw|r for the panel")
	if stale and stale > 0 then
		Print("|cffffcc00your data is a level-" .. tostring(Data.character.level)
			.. " snapshot and you are level " .. tostring(FC:PlayerLevel())
			.. " — re-run the armory refresh|r")
	end
	if FC.SyncMinimapButton then
		FC:SyncMinimapButton()
	end
	-- Open once on the very first login so the addon is impossible to miss.
	if not DB().autoOpened and FC.Toggle then
		DB().autoOpened = true
		DB().everShown = true
		FC:Toggle()
	end
end

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("ADDON_LOADED")
eventFrame:RegisterEvent("PLAYER_LOGIN")

eventFrame:SetScript("OnEvent", function(_, event, arg1)
	local ok, err = pcall(function()
		if event == "ADDON_LOADED" then
			if arg1 == "ForeverCompanion" then
				InitDB()
			end
		elseif event == "PLAYER_LOGIN" then
			OnLogin()
		end
	end)
	if not ok then
		FC.lastError = tostring(err)
		Print("|cffff5555error|r in " .. tostring(event) .. ": " .. tostring(err))
	end
end)

SLASH_FOREVERCOMPANION1 = "/fw"
SLASH_FOREVERCOMPANION2 = "/forever"
SlashCmdList["FOREVERCOMPANION"] = function(message)
	local ok, err = pcall(FC.HandleCommand, FC, message)
	if not ok then
		FC.lastError = tostring(err)
		Print("|cffff5555error|r: " .. tostring(err))
	end
end
