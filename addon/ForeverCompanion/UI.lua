-- ForeverCompanion / UI.lua
-- One movable panel with four tabs: Next / Gear / Farm / Profs, plus a minimap
-- button so there is always something to click.
--
-- Built from plain frames and font strings on purpose: no XML, no template
-- chains that break on patch day. Every risky API call is wrapped in pcall and
-- the failure is reported in chat instead of vanishing.

local FC = ForeverCompanion
local Data = ForeverCompanionData

local WIDTH, HEIGHT = 448, 560
local ROW_HEIGHT = 36
local ROW_INDENT = 10
local TAB_HEIGHT = 22
local ICON = "Interface\\Icons\\INV_Misc_Map_01"

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

local function DB()
	return ForeverCompanionDB or FC:InitDB()
end

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
	local name = link:match("%[(.-)%]")
	return name
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
			where = where .. " · needs " .. tostring(entry.reqLevel)
		end
		if entry.verification and entry.verification ~= "armory" then
			where = where .. " · " .. tostring(entry.verification)
		end
		table.insert(rows, {
			title = colour .. "[P" .. tostring(entry.priority) .. "]|r "
				.. WHITE .. tostring(entry.label or entry.slot or "?") .. "|r → "
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
		if live and slot.name and live ~= slot.name then
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
			title = WHITE .. tostring(zone.name) .. "|r  " .. GREY
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
			title = WHITE .. tostring(prof.profession) .. "|r  " .. GREY
				.. tostring(prof.current) .. "/" .. tostring(prof.cap) .. "|r",
			detail = GREY .. Cut(prof.action or "", 96) .. "|r",
		})
	end
	return rows
end

-- ------------------------------------------------------------------ panel

local function BuildPanel()
	local template = BackdropTemplateMixin and "BackdropTemplate" or nil
	local frame = CreateFrame("Frame", "ForeverCompanionFrame", UIParent, template)
	frame:SetSize(WIDTH, HEIGHT)
	frame:SetPoint("CENTER")
	frame:SetFrameStrata("FULLSCREEN_DIALOG")
	if frame.SetToplevel then frame:SetToplevel(true) end
	frame:EnableMouse(true)
	frame:SetMovable(true)
	frame:SetClampedToScreen(true)
	frame:RegisterForDrag("LeftButton")

	if frame.SetBackdrop then
		pcall(function()
			frame:SetBackdrop({
				bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
				edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
				tile = true, tileSize = 32, edgeSize = 32,
				insets = { left = 11, right = 12, top = 12, bottom = 11 },
			})
		end)
	end

	frame:SetScript("OnDragStart", function(self) self:StartMoving() end)
	frame:SetScript("OnDragStop", function(self)
		self:StopMovingOrSizing()
		local point, _, relPoint, x, y = self:GetPoint()
		DB().position = { point = point, relPoint = relPoint, x = x, y = y }
	end)

	local saved = DB().position
	if saved then
		frame:ClearAllPoints()
		frame:SetPoint(saved.point or "CENTER", UIParent, saved.relPoint or "CENTER",
			saved.x or 0, saved.y or 0)
	end

	local title = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
	title:SetPoint("TOPLEFT", 18, -14)
	title:SetText(GOLD .. "Forever Companion|r")
	frame.title = title

	local subtitle = frame:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
	subtitle:SetPoint("TOPLEFT", title, "BOTTOMLEFT", 0, -2)
	subtitle:SetText(GREY .. "loading|r")
	frame.subtitle = subtitle

	-- close button: the template name is a string, not a global, so always try it
	local okClose, close = pcall(CreateFrame, "Button", nil, frame, "UIPanelCloseButton")
	if okClose and close then
		close:SetPoint("TOPRIGHT", -6, -6)
		close:SetScript("OnClick", function() frame:Hide() end)
	end
	if UISpecialFrames then
		table.insert(UISpecialFrames, "ForeverCompanionFrame")
	end

	local tabs = { { key = "next", label = "Next" }, { key = "gear", label = "Gear" },
		{ key = "farm", label = "Farm" }, { key = "profs", label = "Profs" } }
	frame.tabButtons = {}
	local last
	for _, tab in ipairs(tabs) do
		local button = CreateFrame("Button", nil, frame)
		button:SetSize(96, TAB_HEIGHT)
		if last then
			button:SetPoint("LEFT", last, "RIGHT", 4, 0)
		else
			button:SetPoint("TOPLEFT", 16, -56)
		end
		pcall(function()
			button:SetNormalFontObject(GameFontNormal)
		end)
		local label = button:CreateFontString(nil, "OVERLAY", "GameFontNormal")
		label:SetAllPoints()
		label:SetText(tab.label)
		button.label = label
		button:SetScript("OnClick", function()
			FC.tab = tab.key
			frame:Refresh()
		end)
		pcall(function()
			button:SetHighlightTexture(
				"Interface\\PaperDollInfoFrame\\UI-Character-Tab-Highlight")
		end)
		frame.tabButtons[tab.key] = button
		last = button
	end

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
		local nextScroll = (self:GetVerticalScroll() or 0) - (delta * 45)
		if nextScroll < 0 then nextScroll = 0 end
		if nextScroll > range then nextScroll = range end
		self:SetVerticalScroll(nextScroll)
	end)

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
		local ok, frame = pcall(BuildPanel)
		if not ok then
			self.lastError = tostring(frame)
			Print("panel failed to build: " .. tostring(frame))
			return
		end
		self.frame = frame
	end
	if self.frame:IsShown() then
		self.frame:Hide()
	else
		self.frame:Show()
		self:RefreshPanel()
	end
end

function FC:ShowTab(tab)
	self.tab = tab or "next"
	if not self.frame then
		self:Toggle()
		return
	end
	self.frame:Show()
	self:RefreshPanel()
end

function FC:ResetPosition()
	if not self.frame then
		return
	end
	self.frame:ClearAllPoints()
	self.frame:SetPoint("CENTER")
end

-- ------------------------------------------------------------------ minimap

function FC:SyncMinimapButton()
	local db = DB()
	if not db.minimap then
		if self.minimapButton then self.minimapButton:Hide() end
		return
	end
	if not self.minimapButton then
		local ok, button = pcall(function()
			if not Minimap then
				return nil
			end
			local frame = CreateFrame("Button", "ForeverCompanionMinimapButton", Minimap)
			frame:SetSize(28, 28)
			frame:SetFrameStrata("MEDIUM")
			if Minimap.GetFrameLevel then
				frame:SetFrameLevel(Minimap:GetFrameLevel() + 5)
			end
			frame:SetPoint("CENTER", Minimap, "CENTER", 0, -78)
			frame:SetNormalTexture(ICON)
			frame:SetPushedTexture(ICON)
			frame:SetScript("OnClick", function() FC:Toggle() end)
			frame:SetScript("OnEnter", function(self)
				if GameTooltip then
					GameTooltip:SetOwner(self, "ANCHOR_LEFT")
					GameTooltip:AddLine("Forever Companion")
					GameTooltip:AddLine("/fw — open the plan", 1, 1, 1)
					GameTooltip:Show()
				end
			end)
			frame:SetScript("OnLeave", function()
				if GameTooltip then GameTooltip:Hide() end
			end)
			return frame
		end)
		if ok and button then
			self.minimapButton = button
		elseif not ok then
			self.lastError = tostring(button)
		end
	end
	if self.minimapButton then
		self.minimapButton:Show()
	end
end
