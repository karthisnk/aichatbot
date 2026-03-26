import React, { useState } from 'react';
import { 
  Plus, 
  Paperclip, 
  Mic, 
  Send, 
  History,
  Phone,
  Bell,
  ChevronDown,
  Menu,
  ChevronsLeft,
  MoreHorizontal,
  Settings,
  HelpCircle,
  GraduationCap,
  Search,
  ArrowDown,
  Users,
  Calendar,
  AlertCircle,
  AlertTriangle,
  X
} from 'lucide-react';

// --- Precise 1:1 Official Branding Assets ---

const FreseniusLogo = () => (
  <div className="flex items-center gap-[14px]">
    {/* Exact geometrically accurate SVG of the FMC emblem */}
    <svg width="44" height="30" viewBox="0 0 480 320" fill="white" className="shrink-0">
      <path d="M 0 40 H 480 L 420 100 L 240 145 L 60 100 Z" />
      <path d="M 90 130 L 240 167.5 L 390 130 L 342 178 L 240 215.5 L 138 178 Z" />
      <path d="M 168 208 L 240 245.5 L 312 208 L 240 280 Z" />
    </svg>
    <div className="flex flex-col justify-center">
      <span className="text-[17px] font-[900] leading-none tracking-[0.02em] antialiased text-white">FRESENIUS</span>
      <span className="text-[10.5px] font-[800] leading-tight tracking-[0.09em] antialiased text-white mt-[3px] opacity-95">MEDICAL CARE</span>
    </div>
  </div>
);

// Exact Left Sidebar Icons
const ChatIcon = ({ active }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={active ? "text-white" : "text-white/80"}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const CyclerIcon = ({ active }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={active ? "text-white" : "text-white/80"}>
    <rect x="5" y="4" width="14" height="8" rx="1.5" />
    <path d="M12 7v2" />
    <path d="M8 12v3" />
    <path d="M16 12v3" />
    <path d="M4 16h16" />
    <path d="M4 20h16" />
  </svg>
);

const AdminIcon = ({ active }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={active ? "text-white" : "text-white/80"}>
    <path d="M9 22c-4-2-6-6-6-11V5l8-3 8 3v4" />
    <circle cx="16" cy="16" r="6" />
    <circle cx="16" cy="14" r="1.5" />
    <path d="M13.5 19c.5-1.5 1.5-2 2.5-2s2 .5 2.5 2" />
  </svg>
);

// Dashboard Body Icons
const ListIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-600">
    <line x1="8" y1="6" x2="21" y2="6" /><line x1="8" y1="12" x2="21" y2="12" /><line x1="8" y1="18" x2="21" y2="18" />
    <line x1="3" y1="6" x2="3.01" y2="6" /><line x1="3" y1="12" x2="3.01" y2="12" /><line x1="3" y1="18" x2="3.01" y2="18" />
  </svg>
);

const TherapyGapIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-gray-500">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" opacity="0.4" />
    <line x1="3" y1="3" x2="21" y2="21" stroke="currentColor" strokeWidth="2" />
  </svg>
);


const App = () => {
  const [currentPage, setCurrentPage] = useState('chat'); // Default to Chat for development
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(false);
  const [isChatHistoryVisible, setIsChatHistoryVisible] = useState(true);
  const [isFaqExpanded, setIsFaqExpanded] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  
  const recentChats = [
    "Patient Smith Lab Results",
    "Dialysis Equipment Inquiry",
    "Insurance Coverage Question"
  ];

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;
    const newMessage = { id: Date.now(), text: inputValue, sender: 'user' };
    setMessages([...messages, newMessage]);
    setInputValue('');
    
    setTimeout(() => {
      setMessages(prev => [...prev, { 
        id: Date.now() + 1, 
        text: "I have reviewed the clinical logs. No active alarms for the requested patient in the last 7 days.", 
        sender: 'ai' 
      }]);
    }, 1000);
  };

  return (
    <div className="h-screen flex flex-col font-sans overflow-hidden text-[#333]">
      {/* HEADER - MATCHING EXACT COLOR AND LAYOUT */}
      <header className="bg-[#003DA5] h-14 flex items-center justify-between px-4 text-white shrink-0 z-50">
        <FreseniusLogo />
        <div className="flex items-center gap-6 text-[13px] mr-2">
          <div className="flex items-center gap-1 cursor-pointer">
            <span className="font-medium">Apollo</span>
            <ChevronDown size={14} />
          </div>
          <div className="relative cursor-pointer">
            <Bell size={18} />
            <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-red-500 rounded-full"></span>
          </div>
          {/* User Avatar Circle */}
          <div className="flex items-center justify-center w-[26px] h-[26px] bg-[#B3D4FF] text-[#003DA5] rounded-full font-bold text-[10px] cursor-pointer">
            KN
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* SIDEBAR - PRECISE BACKGROUND COLOR AND CORRECT ACTIVE STATE */}
        <aside className={`bg-[#5D6D84] text-white flex flex-col transition-all duration-300 ${isSidebarExpanded ? 'w-64' : 'w-16'} shrink-0 z-40`}>
          <div className={`flex w-full py-5 mb-1 ${isSidebarExpanded ? 'px-6 justify-start' : 'justify-center'}`}>
            <button 
              onClick={() => setIsSidebarExpanded(!isSidebarExpanded)} 
              className="text-white hover:text-gray-300 transition-colors"
            >
              {isSidebarExpanded ? <ChevronsLeft size={22} /> : <Menu size={22} />}
            </button>
          </div>

          <nav className="flex flex-col gap-1 w-full">
            <SidebarItem 
              icon={<ChatIcon active={currentPage === 'chat'} />} 
              label="Chat" 
              active={currentPage === 'chat'} 
              expanded={isSidebarExpanded}
              onClick={() => setCurrentPage('chat')} 
            />
            
            <SidebarItem 
              icon={<CyclerIcon active={currentPage === 'summary'} />} 
              label="Treatments" 
              active={currentPage === 'summary'} 
              expanded={isSidebarExpanded}
              onClick={() => setCurrentPage('summary')} 
            />
            
            <div className={`my-3 border-t border-white/20 ${isSidebarExpanded ? 'mx-6' : 'mx-4'}`}></div>
            
            <SidebarItem 
              icon={<AdminIcon active={false} />} 
              label="Administration" 
              expanded={isSidebarExpanded}
              hasDropdown={true}
            />
            
            <SidebarItem 
              icon={<Settings size={22} className="text-white/80" />} 
              label="Settings" 
              expanded={isSidebarExpanded} 
              hasDropdown={true}
            />
            
            <SidebarItem 
              icon={<HelpCircle size={22} className="text-white/80" />} 
              label="User Manuals" 
              expanded={isSidebarExpanded} 
            />
            
            <div className={`my-3 border-t border-white/20 ${isSidebarExpanded ? 'mx-6' : 'mx-4'}`}></div>

            <SidebarItem 
              icon={<div className="w-[22px] h-[22px]" />} 
              label="About" 
              expanded={isSidebarExpanded} 
            />
          </nav>
        </aside>

        {/* MAIN CONTENT AREA */}
        <main className="flex-1 flex flex-col overflow-hidden bg-[#F5F6F8]">
          {currentPage === 'summary' ? (
            <div className="flex-1 overflow-auto p-8">
              <h1 className="text-[26px] font-bold text-gray-800 mb-6">Apollo</h1>
              
              <div className="flex gap-8 mb-6 border-b border-gray-200 px-1">
                <div className="pb-3 border-b-[3px] border-[#003DA5] text-[#003DA5] font-bold text-sm cursor-pointer">Summary</div>
                <div className="pb-3 text-gray-500 font-medium text-sm cursor-pointer hover:text-gray-700">Treatments ( • 1 )</div>
                <div className="pb-3 text-gray-500 font-medium text-sm cursor-pointer hover:text-gray-700">Patients</div>
                <div className="pb-3 text-gray-500 font-medium text-sm cursor-pointer hover:text-gray-700">Equipment</div>
              </div>

              <div className="grid grid-cols-12 gap-6">
                <div className="col-span-12 lg:col-span-3">
                  <div className="bg-white rounded-md border border-gray-200 p-5">
                    <h3 className="text-[15px] font-bold text-gray-800 mb-4">Patients</h3>
                    
                    <div className="space-y-3">
                      <div className="border border-blue-500 rounded-md p-3 px-4">
                        <span className="text-blue-600 font-bold text-[12px] block mb-1">All</span>
                        <div className="flex items-center gap-2 text-gray-800">
                          <ListIcon />
                          <span className="text-[22px] font-bold">32</span>
                        </div>
                      </div>

                      <div className="border border-gray-200 rounded-md p-3 px-4">
                        <span className="text-blue-600 font-bold text-[12px] block mb-1">Therapy Gaps</span>
                        <div className="flex items-center gap-2 text-gray-800">
                          <TherapyGapIcon />
                          <span className="text-[22px] font-bold">5</span>
                        </div>
                      </div>

                      <div className="border border-gray-200 rounded-md p-3 px-4">
                        <span className="text-blue-600 font-bold text-[12px] block mb-1">First 90 Days</span>
                        <div className="flex items-center gap-2 text-gray-800">
                          <GraduationCap size={20} className="text-gray-500" strokeWidth={2} />
                          <span className="text-[22px] font-bold">0</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="col-span-12 lg:col-span-9">
                  <div className="bg-white rounded-md border border-gray-200 flex flex-col h-full">
                    {/* Panel Header */}
                    <div className="flex justify-between items-center p-4 border-b border-gray-100">
                      <h2 className="font-bold text-[15px] text-gray-800">Alerts & Alarms - Last 7 Days</h2>
                      <div className="flex bg-gray-50 border border-gray-200 rounded text-[12px] font-medium">
                        <button className="px-3 py-1.5 bg-white border-r border-gray-200 text-gray-700 flex items-center gap-1.5">
                          <Users size={14}/> By Patients
                        </button>
                        <button className="px-3 py-1.5 text-gray-400 flex items-center gap-1.5 hover:bg-gray-100">
                          <Calendar size={14}/> By Date
                        </button>
                      </div>
                    </div>
                    
                    {/* Panel Body */}
                    <div className="flex-1 min-h-[250px] flex flex-col items-center justify-center border-b border-gray-100">
                       <p className="text-gray-400 text-[13px]">No treatments with alerts and alarms within the last 7 days.</p>
                    </div>
                    
                    {/* Panel Footer */}
                    <div className="px-4 py-2.5 bg-[#FAFAFA] flex justify-between items-center text-[11px] text-gray-500">
                       <span>0 Patients | 0 Treatments</span>
                       <div className="flex items-center gap-5">
                          <span className="flex items-center gap-1.5"><AlertCircle size={14} className="text-gray-400"/> Clinical Alerts</span>
                          <span className="flex items-center gap-1.5"><AlertTriangle size={14} className="text-red-600"/> Cycler Alarms</span>
                          <span className="flex items-center gap-1.5"><AlertTriangle size={14} className="text-yellow-500"/> Cycler Cautions</span>
                       </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Table Section */}
              <div className="mt-8">
                <h2 className="font-bold text-[15px] text-gray-800 mb-4">Last 7 Days Treatments (0)</h2>
                
                <div className="flex justify-between items-center mb-4">
                   <div className="relative">
                      <Search size={14} className="absolute left-3 top-[10px] text-gray-400" />
                      <input 
                        type="text" 
                        placeholder="Search by patient..." 
                        className="pl-8 pr-4 py-2 border border-gray-200 rounded-md text-[13px] w-[280px] focus:outline-none focus:border-blue-500" 
                      />
                   </div>
                   <div className="flex gap-2">
                      <button className="px-5 py-2 bg-gray-200 text-gray-400 rounded-full text-[12px] font-bold cursor-not-allowed">Mark as Reviewed</button>
                      <button className="px-5 py-2 bg-white border border-gray-200 text-gray-400 rounded-full text-[12px] font-bold cursor-not-allowed">Mark as Un-Reviewed</button>
                   </div>
                </div>
                
                <div className="border-t border-b border-gray-200 py-3.5 flex text-[12px] font-bold text-gray-700 px-4">
                   <div className="w-[12%] flex items-center gap-1">Date, Start <ArrowDown size={14}/></div>
                   <div className="w-[8%]">DUR, min</div>
                   <div className="w-[18%]">Patient Name</div>
                   <div className="w-[8%]">Alarms</div>
                   <div className="w-[8%]">Notes</div>
                   <div className="w-[10%]">Weight, kg</div>
                   <div className="w-[10%]">BP, mmHg</div>
                   <div className="w-[10%]">Pulse, bpm</div>
                   <div className="w-[6%]">UF, L</div>
                   <div className="w-[10%]">Dialysate, L</div>
                   <div className="w-[10%]">Blood, L</div>
                </div>
                
                <div className="py-12 flex justify-center text-gray-500 text-[13px]">
                   No available treatments.
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-1 overflow-hidden bg-white">
              {/* Gemini Chat Sidebar */}
              <div className={`${isChatHistoryVisible ? 'w-72' : 'w-0'} transition-all duration-300 border-r bg-gray-50 flex flex-col overflow-hidden`}>
                <div className="p-4">
                  <button 
                    onClick={() => setMessages([])}
                    className="w-full flex items-center justify-center gap-2 bg-[#003DA5] text-white px-4 py-2.5 rounded-full text-sm font-bold hover:bg-[#002b75] transition-all shadow-sm"
                  >
                    <Plus size={18} />
                    <span>New Chat</span>
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto px-4 pb-4">
                  <p className="text-[11px] font-bold text-gray-500 mb-3 px-1">Recent Chats</p>
                  <div className="space-y-1">
                    {recentChats.map((chat, idx) => (
                      <div key={idx} className="flex items-center gap-3 p-2.5 hover:bg-gray-200 rounded-lg cursor-pointer text-[13px] text-gray-700 transition-all">
                        <History size={14} className="text-gray-400" />
                        <span className="truncate">{chat}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Chat Viewport */}
              <div className="flex-1 flex flex-col relative">
                {/* Updated Toggle with History Icon and New Chat button when collapsed */}
                <div className="absolute left-4 top-4 z-10 flex items-center gap-2">
                  <button 
                    onClick={() => setIsChatHistoryVisible(!isChatHistoryVisible)}
                    className="p-2 hover:bg-gray-100 rounded-md text-gray-500 transition-all border border-transparent hover:border-gray-200"
                    title={isChatHistoryVisible ? "Hide history" : "Show history"}
                  >
                    <History size={20} />
                  </button>
                  {!isChatHistoryVisible && (
                    <button 
                      onClick={() => setMessages([])}
                      className="p-2 hover:bg-gray-100 rounded-md text-gray-500 transition-all border border-transparent hover:border-gray-200"
                      title="New Chat"
                    >
                      <Plus size={20} />
                    </button>
                  )}
                </div>

                <div className="h-14 border-b border-gray-200 flex items-center justify-end px-6">
                  <button 
                    onClick={() => setIsFaqExpanded(!isFaqExpanded)}
                    className={`flex items-center gap-2 text-[13px] font-bold px-3 py-1.5 rounded-md transition-all ${isFaqExpanded ? 'bg-blue-50 text-[#003DA5]' : 'text-gray-600 hover:bg-gray-100'}`}
                  >
                    <HelpCircle size={16} />
                    <span>FAQs</span>
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 md:p-10 space-y-8 flex flex-col items-center">
                  {messages.length === 0 ? (
                    <div className="mt-16 text-center space-y-4 max-w-xl">
                      <h2 className="text-[32px] font-bold text-gray-800">
                        Hello
                      </h2>
                      <p className="text-[15px] text-gray-500">How can I assist you with clinical data today?</p>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-12 text-left">
                        {[
                          { title: "Summarize alerts", desc: "View clinical warnings from today." },
                          { title: "Lab Results", desc: "Compare hemoglobin levels across clinics." }
                        ].map((card, i) => (
                          <div key={i} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-all">
                            <p className="text-[13px] font-bold text-gray-800">{card.title}</p>
                            <p className="text-[12px] text-gray-500 mt-1">{card.desc}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="w-full max-w-3xl space-y-6 pb-12">
                      {messages.map((m) => (
                        <div key={m.id} className={`flex gap-4 ${m.sender === 'user' ? 'justify-end' : ''}`}>
                          {m.sender === 'ai' && (
                            <div className="w-8 h-8 rounded-full bg-[#003DA5] flex items-center justify-center shrink-0">
                              <svg width="14" height="14" viewBox="0 0 54 38" fill="white">
                                <path d="M0 4.5L27 33L54 4.5H41L27 19L13 4.5H0Z" />
                              </svg>
                            </div>
                          )}
                          <div className={`max-w-[80%] px-4 py-2.5 rounded-lg text-[14px] ${
                            m.sender === 'user' 
                            ? 'bg-blue-50 text-blue-900 border border-blue-100' 
                            : 'bg-white border border-gray-200 text-gray-800'
                          }`}>
                            {m.text}
                          </div>
                          {m.sender === 'user' && (
                            <div className="w-8 h-8 rounded-full bg-[#B3D4FF] text-[#003DA5] flex items-center justify-center shrink-0 text-[10px] font-bold">
                              KN
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="px-6 pb-6 flex flex-col items-center w-full">
                  <div className="w-full max-w-3xl bg-white rounded-lg p-1.5 px-4 flex items-end gap-2 border border-gray-300 shadow-sm focus-within:border-blue-500 transition-all">
                    <button className="mb-1 p-2 text-gray-400 hover:text-gray-600 rounded transition-colors">
                      <Plus size={20} />
                    </button>
                    <textarea 
                      value={inputValue}
                      onChange={(e) => setInputValue(e.target.value)}
                      placeholder="Ask Apollo..."
                      className="flex-1 bg-transparent border-none focus:ring-0 resize-none py-2.5 text-gray-800 min-h-[44px] max-h-48 text-[14px]"
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                    />
                    <div className="flex items-center gap-1 mb-1">
                      <button className="p-2 text-gray-400 hover:text-gray-600 rounded transition-colors"><Mic size={20} /></button>
                      <button className="p-2 text-gray-400 hover:text-gray-600 rounded transition-colors"><Paperclip size={20} /></button>
                      <button 
                        onClick={handleSendMessage}
                        disabled={!inputValue.trim()}
                        className={`p-2 rounded transition-all ${inputValue.trim() ? 'text-[#003DA5] hover:bg-blue-50' : 'text-gray-300 cursor-not-allowed'}`}
                      >
                        <Send size={20} />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* FAQ Right Sidebar */}
              <div className={`${isFaqExpanded ? 'w-80' : 'w-0'} transition-all duration-300 border-l border-gray-200 bg-[#F9FAFB] flex flex-col overflow-hidden shrink-0`}>
                <div className="px-5 h-14 border-b border-gray-200 flex justify-between items-center bg-white shrink-0">
                  <h3 className="font-bold text-[#003DA5] flex items-center gap-2 text-[14px]">
                    <HelpCircle size={16}/> Frequently Asked Questions
                  </h3>
                  <button onClick={() => setIsFaqExpanded(false)} className="text-gray-400 hover:text-gray-600 p-1.5 rounded-md hover:bg-gray-100 transition-colors">
                    <X size={18} />
                  </button>
                </div>
                <div className="p-5 overflow-y-auto space-y-4">
                  {[
                    { q: "What can Apollo help me with?", a: "Apollo can summarize clinical alerts, analyze patient lab trends, and answer questions about treatment histories." },
                    { q: "How do I filter treatments by date?", a: "Navigate to the Summary tab and use the 'By Date' toggle under the Alerts & Alarms panel." },
                    { q: "What does a 'Therapy Gap' mean?", a: "A therapy gap indicates a missed or incomplete dialysis session based on the patient's individual prescription." },
                    { q: "Can I export patient data?", a: "Yes, you can export compliance reports and alert histories from the Administration panel under 'Data Exports'." }
                  ].map((faq, i) => (
                    <div key={i} className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm hover:border-blue-200 transition-colors cursor-pointer group">
                      <h4 className="font-bold text-[13px] text-gray-800 mb-1.5 group-hover:text-[#003DA5] transition-colors">{faq.q}</h4>
                      <p className="text-[12px] text-gray-500 leading-relaxed">{faq.a}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

// PRECISE Sidebar Item - Grouping & Dropdown Support
const SidebarItem = ({ icon, label, active, expanded, onClick, hasDropdown }) => (
  <div className="w-full flex justify-center py-[2px]">
    <div 
      onClick={onClick}
      className={`flex items-center cursor-pointer transition-colors ${
        expanded ? 'justify-between w-full mx-4 px-3 py-2.5 rounded-md' : 'justify-center w-[44px] h-[44px] rounded-[10px]'
      } ${
        active 
        ? 'bg-[#3A4B61] text-white' 
        : 'hover:bg-white/10 text-white/80 hover:text-white'
      }`}
    >
      <div className="flex items-center shrink-0">
        <div className="flex items-center justify-center">
          {icon}
        </div>
        {expanded && (
          <span className="whitespace-nowrap text-[14.5px] font-normal tracking-wide ml-4">
            {label}
          </span>
        )}
      </div>
      {expanded && hasDropdown && (
        <ChevronDown size={18} className="text-white/80 shrink-0 mr-1" />
      )}
    </div>
  </div>
);

export default App;