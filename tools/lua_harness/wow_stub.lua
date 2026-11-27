-- Minimal World of Warcraft API stub, enough to boot an addon headless.
-- Not a game client: it exists to catch nil errors, bad API calls and logic bugs
-- in the code paths the harness exercises (events, slash commands, panel render).

local chat = {}
local frames = {}

Harness = {
	chat = chat,
	frames = frames,
	unitLevel = 23,
	links = {},
	maxRows = 0,
	secretToken = {},
	returnSecret = false,
}
Harness.__index = Harness

UISpecialFrames = {}
GameFontNormal = {}
GameFontHighlightSmall = {}
GameTooltip = {
	SetOwner = function() end,
	AddLine = function() end,
	Show = function() end,
	Hide = function() end,
}
Minimap = {
	GetFrameLevel = function() return 1 end,
	GetWidth = function() return 140 end,
}
SlashCmdList = {}
UIPanelCloseButton = true
BackdropTemplateMixin = true
UIParent = {}

DEFAULT_CHAT_FRAME = {
	AddMessage = function(_, message)
		chat[#chat + 1] = tostring(message)
	end,
}

local function NewRegion(kind)
	local region = { kind = kind, shown = true, text = nil }
	function region:SetText(value) self.text = value end
	function region:GetText() return self.text end
	function region:SetPoint() end
	function region:ClearAllPoints() end
	function region:GetPoint() return "CENTER", nil, "CENTER", 0, 0 end
	function region:SetWidth() end
	function region:SetHeight() end
	function region:GetWidth() return 100 end
	function region:GetHeight() return 20 end
	function region:SetAllPoints() end
	function region:SetJustifyH() end
	function region:SetTextColor() end
	function region:SetHighlightTexture() end
	function region:Show() self.shown = true end
	function region:Hide() self.shown = false end
	function region:IsShown() return self.shown end
	return region
end

local function NewFrame(frameType, name, parent)
	local frame = NewRegion(frameType)
	frame.name = name
	frame.parent = parent
	frame.scripts = {}
	frame.events = {}

	function frame:SetSize(width, height) self.width, self.height = width, height end
	function frame:SetFrameStrata() end
	function frame:EnableMouse() end
	function frame:SetMovable() end
	function frame:SetClampedToScreen() end
	function frame:RegisterForDrag() end
	function frame:SetScript(key, fn) self.scripts[key] = fn end
	function frame:GetScript(key) return self.scripts[key] end
	function frame:StartMoving() end
	function frame:StopMovingOrSizing() end
	function frame:SetBackdrop() end
	function frame:EnableMouseWheel() end
	function frame:SetScrollChild(child) self.scrollChild = child end
	function frame:GetVerticalScroll() return self.vscroll or 0 end
	function frame:SetVerticalScroll(value) self.vscroll = value end
	function frame:GetVerticalScrollRange() return self.range or 600 end
	function frame:RegisterEvent(event) self.events[event] = true end
	function frame:SetFrameLevel(level) self.frameLevel = level end
	function frame:GetFrameLevel() return self.frameLevel or 1 end
	function frame:SetNormalTexture(value) self.normalTexture = value end
	function frame:SetPushedTexture(value) self.pushedTexture = value end
	function frame:CreateFontString() return NewRegion("FontString") end
	function frame:CreateTexture() return NewRegion("Texture") end
	function frame:CreateFrame(ftype) return NewFrame(ftype) end

	frames[#frames + 1] = frame
	if name then
		_G[name] = frame
	end
	return frame
end

function CreateFrame(frameType, name, parent)
	return NewFrame(frameType, name, parent)
end

function Harness:GetChatText()
	return table.concat(chat, "\n")
end

function Harness:FireEvent(event, arg1)
	local fired = 0
	for _, frame in ipairs(frames) do
		local script = frame.scripts and frame.scripts["OnEvent"]
		if script then
			script(frame, event, arg1)
			fired = fired + 1
		end
	end
	return fired
end

function Harness:FireEventOn(name, event, arg1)
	local frame = _G[name]
	if not frame then
		return false
	end
	local script = frame.scripts["OnEvent"]
	if script then
		script(frame, event, arg1)
		return true
	end
	return false
end

function Harness:FireScript(name, scriptName, ...)
	local frame = _G[name]
	if not frame then
		return false
	end
	local script = frame.scripts[scriptName]
	if script then
		script(frame, ...)
		return true
	end
	return false
end

function Harness:ResetChat()
	for index = #chat, 1, -1 do
		chat[index] = nil
	end
end

-- API surface the addon may touch -------------------------------------------

function time(t) return os.time(t) end
function issecretvalue(value) return value == Harness.secretToken end
function UnitLevel()
	if Harness.returnSecret then
		return Harness.secretToken
	end
	return Harness.unitLevel
end
function GetAddOnMetadata(_, field)
	if field == "Version" then return "0.1.1" end
	return nil
end
function UnitName() return "Mavo Music" end
function GetInventoryItemLink(_, slot) return Harness.links[slot] end
function GetBuildInfo() return "1.60.1", "16001", "Sep 1 2026", 16001 end
