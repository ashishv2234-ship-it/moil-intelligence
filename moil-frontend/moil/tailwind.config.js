export default { darkMode:['class','[data-theme="dark"]'], content:['./index.html','./src/**/*.{ts,tsx}'],
theme:{extend:{fontFamily:{sans:['"Segoe UI"','Roboto','"Helvetica Neue"','Arial','sans-serif']},
borderRadius:{DEFAULT:'2px',sm:'2px',md:'2px',lg:'3px',xl:'3px'},
boxShadow:{lg:'0 1px 3px rgba(0,0,0,.25)'},
colors:{ink:'var(--ink)',panel:'var(--panel)',line:'var(--line)',fg:'var(--fg)',mute:'var(--mute)',mn:'var(--mn)',
ok:'#2E9B5E',warn:'#C99A2E',high:'#E07B2D',crit:'#D6453D',info:'#3B82C4'}}}}
