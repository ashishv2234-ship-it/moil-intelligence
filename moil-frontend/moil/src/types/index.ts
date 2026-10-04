export type Role='admin'|'mine_manager'|'geologist'|'planning_engineer'|'maintenance_engineer'|'executive'|'data_engineer'
export type Severity='Low'|'Medium'|'High'|'Critical'
export interface User{id:string;name:string;email:string;role:Role}
export interface Bench{id:string;name:string;rl:number}
export interface Pit{id:string;name:string;benches:Bench[]}
export interface Mine{id:string;name:string;state:string;lat:number;lng:number;dailyTarget:number;pits:Pit[]}
export interface Equipment{id:string;type:'Excavator'|'Dumper'|'Drill'|'Loader'|'Crusher';mineId:string;status:'Running'|'Idle'|'Breakdown'|'Maintenance';availability:number;health:number;downtimeHrs:number;mtbfHrs:number}
export interface ProductionRecord{date:string;mineId:string;planned:number;actual:number}
export interface ProductionForecast{date:string;planned:number;forecast:number;lower:number;upper:number;actual?:number}
export interface ShortfallRisk{id:string;mineId:string;mineName:string;level:Severity;expectedShortfall:number;probability:number;cause:string;confidence:number;action:string;owner:string;status:'Open'|'In Progress'|'Resolved'}
export interface ReserveZone{id:string;lat:number;lng:number;probability:number;tonnage:number;gradeMnPct:number;confidence:'High'|'Medium'|'Low';drillRecommended:boolean;confidencePct?:number;holesNearby?:number;drillSuggested?:boolean;modelVersion?:string;runAt?:string}
export interface DrillHole{id:string;lat:number;lng:number;depthM:number;mnPct:number}
export interface AssayRecord{holeId:string;fromM:number;toM:number;mnPct:number;fePct:number}
export interface WeatherRecord{date:string;mineId:string;rainfallMm:number;blastSuitable:boolean}
export interface BlastRecord{id:string;mineId:string;bench:string;date:string;plannedT:number;actualT?:number;status:'Scheduled'|'Completed'|'Delayed';reason?:string;weather?:{status:'Suitable'|'Caution'|'Unsuitable';observedAt:string;kind:'current'|'forecast';rainMm?:number;windKmh?:number;nextSuitable?:string}}
export interface MaintenanceRecord{equipmentId:string;due:string;task:string;severity:Severity}
export interface CorrectiveAction{id:string;title:string;recoveryT:number;costInrLakh:number;feasibility:'High'|'Medium'|'Low';confidence:number;owner:string;deadline:string;status:'Proposed'|'Approved'|'In Progress'|'Completed'|'Rejected';comments:string[]}
export interface Alert{id:string;severity:Severity;message:string;mineId:string;at:string}
export interface DataSourceStatus{id:string;name:string;lastSync:string;status:'Success'|'Warning'|'Failed';records:number;issues:number}
export interface UploadReport{id:number;kind:string;filename:string;status:'Imported'|'Validated'|'Failed';dryRun:boolean;rowsTotal:number;rowsOk:number;rowsRejected:number;rowsWarning:number;issuesTotal:number;qualityPct:number;createdAt:string}
export interface QualityIssue{row:number;field:string;severity:'Error'|'Warning';message:string}
export interface ReportData{title:string;columns:string[];rows:(string|number)[][];note:string|null;generatedAt:string}
export interface AdminUser{id:number;email:string;name:string;role:Role;isActive:boolean;locked:boolean}
export interface AuditEntry{id:number;at:string;action:string;detail:Record<string,unknown>;userEmail:string|null;userName:string|null}
export interface AuditPage{items:AuditEntry[];total:number;page:number;size:number}

export interface OwnerOption{id:number;name:string;role:string}
export interface ActionComment{id:number;text:string;author:string;role:string|null;createdAt:string}
export interface RiskRun{id:number;at:string;level:Severity;probability:number;expectedShortfall:number;cause:string}
export interface RiskFactor{label:string;points:number}
export interface EquipmentPoint{uploadId:number;at:string;machines:number;availability:number;health:number;breakdowns:number;downtimeHrs:number}
