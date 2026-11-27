-- ForeverCompanion / UI.lua
-- One movable panel with four tabs: Next / Gear / Farm / Profs.
-- Built from plain frames and font strings on purpose: no XML templates beyond
-- the standard close button, so it survives client patches.

local FC = ForeverCompanion
local Data = ForeverCompanionData

local WIDTH, HEIGHT = 448, 560
local ROW_HEIGHT = 36
local ROW_INDENT = 10
local TAB_HEIGHT = 22

local PRIORITY_COLOUR = {
	[1] = "|cffff5555",
	[2] = "|cffffa500",
	[3] = "|cff4da6ff",
	[4] = "|cffb0b0b0",
	[5] = "|cff808080",
}
local GREY = "|cff9d9d9d"
local WHITE = "|cffffffff"
local GREEN = "|cff33ff99"
local GOLD = "|cffffd200"

-- inventory slot ids (stable across clients)
local INV_SLOT = {
	head = 1, neck = 2, shoulder = 3, shirt = 4, chest = 5, waist = 6, legs = 7,
	feet = 8, wrist = 9, hands = 10, ring1 = 11, ring2 = 12, trinket1 = 13,
	trinket2 = 14, back = 15, main_hand = 16, off_hand = 17, tabard = 19,
}

local function Cut(text, limit)
	text = tostring(text or "")
	if #text <= limit then
		return text
	end
	return text:sub(1, limit - 3) .. "..."
end

-- Live equipped item name, read from the item link so we never touch GetItemInfo
-- (its return values can be "secret" on the Midnight client).
local function LiveItemName(slot)
	local invSlot = INV_SLOT[slot]
	if not invSlot or not GetInventoryItemLink then
		return nil
	end
	local ok, link = pcall(GetInventoryItemLink, "player", invSlot)
	if not ok or type(link) ~= "string" then
		return nil
	end
	return link:match("%[(.-)%]")
end

-- ------------------------------------------------------------------ tab data

local function NextRows()
	local rows = {}
	for _, entry in ipairs(FC:OpenPlan(3)) do
		local colour = PRIORITY_COLOUR[entry.priority] or GREY
		local where = entry.how or ""
		if entry.zone and entry.zone ~= "" then
			where = where .. " · " .. entry.zone
		end
		if entry.reqLevel then
			where = where .. " · needs " .. entry.reqLevel
		end
		if entry.verification and entry.verification ~= "armory" then
			where = where .. " · " .. entry.verification
		end
		table.insert(rows, {
			title = colour .. "[P" .. tostring(entry.priority) .. "]|r "
				.. WHITE .. (entry.label or entry.slot or "?") .. "|r → "
				.. GREEN .. tostring(entry.target) .. "|r",
			detail = GREY .. Cut(where, 96) .. "|r",
		})
	end
	if #rows == 0 then
		table.insert(rows, {
			title = GREEN .. "Nothing open. Every step is ticked off.|r",
			detail = GREY .. "/fw reset clears your tick marks|r",
		})
	end
	return rows
end

local function GearRows()
	local rows = {}
	if not Data then return rows end
	for _, slot in ipairs(Data.equipment) do
		local live = LiveItemName(slot.slot)
		local name = live or slot.name
		local state
		if name then
			state = WHITE .. name .. "|r"
		else
			state = "|cffff5555EMPTY|r"
		end
		local detail
		if FC:IsDone("gear:" .. tostring(slot.slot)) then
			detail = GREY .. "checked|r"
		elseif live and live ~= slot.name then
			detail = GOLD .. "changed since snapshot (was " .. tostring(slot.name) .. ")|r"
		else
			detail = GREY .. "as of the armory snapshot|r"
		end
		table.insert(rows, {
			title = GREY .. Cut(slot.label or slot.slot, 12) .. "|r  " .. state,
			detail = detail,
		})
	end
	return rows
end

local function FarmRows()
	local rows = {}
	if not Data then return rows end
	local level = FC:PlayerLevel()
	table.insert(rows, {
		title = GOLD .. "Zones for level " .. tostring(level) .. "|r",
		detail = GREY .. "a little below to a little above|r",
	})
	for _, zone in ipairs(FC:ZonesForLevel()) do
		table.insert(rows, {
			title = WHITE .. (zone.name or "?") .. "|r  " .. GREY
				.. tostring(zone.levelMin) .. "-" .. tostring(zone.levelMax)
				.. " · " .. tostring(zone.faction) .. "|r",
			detail = GREY .. "ore: " .. Cut(zone.mining or "none", 44)
				.. " · " .. Cut(zone.bestFor or "", 44) .. "|r",
		})
	end
	local sources = FC:SourcesForLevel()
	if #sources > 0 then
		table.insert(rows, {
			title = GOLD .. "What drops there|r",
			detail = GREY .. "from the farm-source table|r",
		})
		for index, src in ipairs(sources) do
			if index > 14 then break end
			table.insert(rows, {
				title = WHITE .. Cut(src.item or src.mob or "?", 34) .. "|r  "
					.. GREY .. tostring(src.type or "") .. "|r",
				detail = GREY .. Cut(tostring(src.zone or "-") .. " · "
					.. tostring(src.mob or "") .. " · "
					.. tostring(src.requirement or ""), 96) .. "|r",
			})
		end
	end
	return rows
end

local function ProfRows()
	local rows = {}
	if not Data then return rows end
	for _, prof in ipairs(Data.professionPlan) do
		table.insert(rows, {
			title = WHITE .. (prof.profession or "?") .. "|r  " .. GREY
				.. tostring(prof.current) .. "/" .. tostring(prof.cap) .. "|r",
			detail = GREY .. Cut(prof.action or "", 96) .. "|r",
		})
	end
	return rows
end

-- ------------------------------------------------------------------ panel

local function EnsureBackdrop(frame)
	if not frame.SetBackdrop then
		return
	end
	frame:SetBackdrop({
		bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
		edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
		tile = true, tileSize = 32, edgeSize = 32,
		insets = { left = 11, right = 12, top = 12, bottom = 11 },
	})
end

local function CreatePanel()
	local template = BackdropTemplateMixin and "BackdropTemplate" or nil
	local frame = CreateFrame("Frame", "ForeverCompanionFrame", UIParent, template)
	frame:SetSize(WIDTH, HEIGHT)
	frame:SetPoint("CENTER")
	frame:SetFrameStrata("DIALOG")
	frame:EnableMouse(true)
	frame:SetMovable(true)
	frame:SetClampedToScreen(true)
	frame:RegisterForDrag("LeftButton")
	EnsureBackdrop(frame)

	frame:SetScript("OnDragStart", function(self) self:StartMoving() end)
	frame:SetScript("OnDragStop", function(self)
		self:StopMovingOrSizing()
		local point, _, relPoint, x, y = self:GetPoint()
		local db = ForeverCompanionDB
		if db then
			db.position = { point = point, relPoint = relPoint, x = x, y = y }
		end
	end)

	local db = ForeverCompanionDB
	if db and db.position then
		local pos = db.position
		frame:ClearAllPoints()
		frame:SetPoint(pos.point or "CENTER", UIParent, pos.relPoint or "CENTER",
			pos.x or 0, pos.y or 0)
	end

	-- title
	local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
	title:SetPoint("TOPLEFT", 18, -14)
	title:SetText(GOLD .. "Forever Companion|r")
	frame.title = title

	local subtitle = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	subtitle:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -2)
	if Data then
		subtitle:SetText(GREY .. tostring(Data.character.name) .. " · level "
			.. tostring(Data.character.level) .. " " .. tostring(Data.character.race)
			.. " " .. tostring(Data.character.class) .. "|r")
	end
	frame.subtitle = subtitle

	-- close button
	if UIPanelCloseButton then
		local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
		close:SetPoint("TOPRIGHT", -6, -6)
		close:SetScript("OnClick", function() frame:Hide() end)
	end
	if UISpecialFrames then
		table.insert(UISpecialFrames, "ForeverCompanionFrame")
	end

	-- tabs
	local tabs = { { key = "next", label = "Next" }, { key = "gear", label = "Gear" },
		{ key = "farm", label = "Farm" }, { key = "profs", label = "Profs" } }
	frame.tabButtons = {}
	local last
	for index, tab in ipairs(tabs) do
		local button = CreateFrame("Button", nil, frame)
		button:SetSize(96, TAB_HEIGHT)
		if last then
			button:SetPoint("LEFT", last, "RIGHT", 4, 0)
		else
			button:SetPoint("TOPLEFT", 16, -56)
		end
		button:SetText(tab.label)
		local font = button:CreateFontString(nil, "OVERLAY", "GameFontNormal")
		font:SetAllPoints()
		font:SetText(tab.label)
		button.label = font
		button:SetScript("OnClick", function()
			FC.tab = tab.key
			frame:Refresh()
		end)
		button:SetHighlightTexture("Interface\\PaperDollInfoFrame\\UI-Character-Tab-Highlight")
		frame.tabButtons[tab.key] = button
		last = button
	end

	-- scroll area
	local scroll = CreateFrame("ScrollFrame", nil, frame)
	scroll:SetPoint("TOPLEFT", 14, -84)
	scroll:SetPoint("BOTTOMRIGHT", -32, 40)
	frame.scroll = scroll

	local child = CreateFrame("Frame", nil, scroll)
	child:SetSize(WIDTH - 56, 10)
	scroll:SetScrollChild(child)
	frame.child = child

	scroll:EnableMouseWheel(true)
	scroll:SetScript("OnMouseWheel", function(self, delta)
		local range = self:GetVerticalScrollRange() or 0
		local next = (self:GetVerticalScroll() or 0) - (delta * 45)
		if next < 0 then next = 0 end
		if next > range then next = range end
		self:SetVerticalScroll(next)
	end)

	-- footer
	local footer = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	footer:SetPoint("BOTTOMLEFT", 18, 16)
	footer:SetText(GREY .. "data " .. tostring(Data and Data.generatedAt or "?")
		.. " · /fw help|r")
	frame.footer = footer

	frame.rows = {}

	local function Row(index)
		local row = frame.rows[index]
		if row then return row end
		local y = -6 - ((index - 1) * ROW_HEIGHT)
		local titleFs = child:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
		titleFs:SetPoint("TOPLEFT", child, "TOPLEFT", ROW_INDENT, y)
		titleFs:SetWidth(WIDTH - 80)
		titleFs:SetJustifyH("LEFT")
		local detailFs = child:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
		detailFs:SetPoint("TOPLEFT", titleFs, "BOTTOMLEFT", 0, -2)
		detailFs:SetWidth(WIDTH - 80)
		detailFs:SetJustifyH("LEFT")
		row = { title = titleFs, detail = detailFs }
		frame.rows[index] = row
		return row
	end

	function frame:Refresh()
		local builders = { next = NextRows, gear = GearRows, farm = FarmRows, profs = ProfRows }
		local rows = (builders[FC.tab] or NextRows)()
		local used = #rows
		for index, row in pairs(self.rows) do
			if index > used then
				row.title:Hide()
				row.detail:Hide()
			end
		end
		for index, data in ipairs(rows) do
			local row = Row(index)
			row.title:SetText(data.title or "")
			row.detail:SetText(data.detail or "")
			row.title:Show()
			row.detail:Show()
		end
		self.child:SetHeight(math.max(10, used * ROW_HEIGHT + 12))
		self.scroll:SetVerticalScroll(0)
		for key, button in pairs(self.tabButtons) do
			if key == FC.tab then
				button.label:SetTextColor(1, 0.82, 0)
			else
				button.label:SetTextColor(0.6, 0.6, 0.6)
			end
		end
		if self.subtitle and Data then
			local done, open = FC:PlanCounts()
			self.subtitle:SetText(GREY .. tostring(Data.character.name)
				.. " · level " .. tostring(FC:PlayerLevel()) .. " · "
				.. open .. " open, " .. done .. " done|r")
		end
	end

	frame:Hide()
	return frame
end

function FC:Toggle()
	if not self.frame then
		local ok, frame = pcall(CreatePanel)
		if not ok then
			Print("panel failed to build (" .. tostring(frame) .. ") — chat mode still works")
			return
		end
		self.frame = frame
	end
	if self.frame:IsShown() then
		self.frame:Hide()
	else
		self.frame:Show()
		self.frame:Refresh()
	end
end

function FC:ShowTab(tab)
	self.tab = tab or "next"
	if self.frame then
		self.frame:Show()
		self.frame:Refresh()
	end
end
