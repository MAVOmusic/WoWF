-- ForeverCompanion / Core.lua
-- State, saved variables, plan logic and slash commands.
-- UI lives in UI.lua and is optional: everything here works headless.

local PREFIX = "|cff33ff99Forever|r|cffffd200Companion|r: "

ForeverCompanion = ForeverCompanion or {}
local FC = ForeverCompanion

FC.version = "0.1.0"
FC.frame = nil
FC.tab = "next"

local Data = ForeverCompanionData

local function Print(msg)
	if DEFAULT_CHAT_FRAME then
		DEFAULT_CHAT_FRAME:AddMessage(PREFIX .. tostring(msg))
	else
		print(PREFIX .. tostring(msg))
	end
end
FC.Print = Print

local function Config(msg)
	if DEFAULT_CHAT_FRAME then
		DEFAULT_CHAT_FRAME:AddMessage(PREFIX .. "|cffffffff" .. tostring(msg) .. "|r")
	end
end

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
	local level = UnitLevel and UnitLevel("player")
	if type(level) == "number" and level > 0 then
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
	local thenTime = time({ year = tonumber(y), month = tonumber(m), day = tonumber(d), hour = 12 })
	local nowTime = time()
	if not thenTime or not nowTime then return nil end
	return math.floor((nowTime - thenTime) / 86400)
end

-- ---------------------------------------------------------------- zone filter

-- Zones worth visiting at the player's level (a little below, a little above).
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

-- Farm sources in the player's current band, ore/quest first.
function FC:SourcesForLevel()
	local out = {}
	if not Data then return out end
	local level = self:PlayerLevel() or 1
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

local function ColourByName(name)
	if name == "EMPTY" or not name then
		return "|cffff5555EMPTY|r"
	end
	return "|cffffffff" .. name .. "|r"
end

function FC:ChatStatus()
	local data = Data
	if not data then
		Print("no data loaded (Data.lua missing)")
		return
	end
	local done, open, skipped = self:PlanCounts()
	Config("data build " .. tostring(data.generatedAt)
		.. " · snapshot level " .. tostring(data.character.level)
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
		Print("nothing open — run /fw reset to clear your tick marks")
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
		Config(string.format("  %-11s %s", slot.label or slot.slot, ColourByName(slot.name)))
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
			zone.name, tostring(zone.levelMin), tostring(zone.levelMax),
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
			prof.profession, tostring(prof.current), tostring(prof.cap),
			tostring(prof.action)))
	end
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
end

function FC:HandleCommand(message)
	message = (message or ""):lower():gsub("^%s+", ""):gsub("%s+$", "")
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
	elseif command == "done" or command == "undo" then
		local entry = ResolveEntry(rest)
		if not entry then
			Print("pick an entry with /fw next, then /fw " .. command .. " <index>")
			return
		end
		local isDone = (command == "done")
		self:SetDone(entry.key, isDone)
		if self.frame and self.frame.Refresh then self.frame:Refresh() end
		Print((isDone and "ticked off: " or "reopened: ") .. tostring(entry.target))
	elseif command == "reset" then
		DB().done = {}
		if self.frame and self.frame.Refresh then self.frame:Refresh() end
		Print("all tick marks cleared")
	elseif command == "debug" then
		local db = DB()
		db.debug = not db.debug
		Print("debug " .. (db.debug and "on" or "off"))
	else
		Help()
	end
end

-- ---------------------------------------------------------------- events

local eventFrame = CreateFrame("Frame")
eventFrame:RegisterEvent("ADDON_LOADED")
eventFrame:RegisterEvent("PLAYER_LOGIN")

eventFrame:SetScript("OnEvent", function(_, event, arg1)
	if event == "ADDON_LOADED" then
		if arg1 == "ForeverCompanion" then
			InitDB()
		end
	elseif event == "PLAYER_LOGIN" then
		InitDB()
		if not Data then
			Print("Data.lua did not load — re-run scripts/build_addon_data.py")
			return
		end
		local done, open = FC:PlanCounts()
		local stale = FC:StaleLevelBy()
		local hint = "|cff33ff99/fw|r for the panel, |cff33ff99/fw next|r in chat"
		if stale and stale > 0 then
			Print("your data is a level-" .. tostring(Data.character.level)
				.. " snapshot and you are level " .. tostring(FC:PlayerLevel())
				.. ". " .. open .. " steps still open — " .. hint)
			Print("|cffffcc00re-run the armory refresh to update the plan|r")
		elseif open > 0 then
			Print(open .. " upgrade step(s) open — " .. hint)
		end
		if not DB().everShown then
			DB().everShown = true
		end
	end
end)

SLASH_FOREVERCOMPANION1 = "/fw"
SLASH_FOREVERCOMPANION2 = "/forever"
SlashCmdList["FOREVERCOMPANION"] = function(message)
	FC:HandleCommand(message)
end
