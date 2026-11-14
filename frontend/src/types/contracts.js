/** @typedef {{id:number,name:string,source:string,rows:number,checksum:string}} Dataset */
/** @typedef {{id:number,name:string,dataset_id:number,status:string,result:Object,approved:boolean,revoked_reason:string,revoked_at:number,revoked_by:string}} AnalysisJob */
/** @typedef {{id:number,job_id:number,action:string,reason:string,actor:string,at:number}} ApprovalRecord */
/** @typedef {{id:number,name:string,job_id:number,destination:string,next_run:number,enabled:boolean,blocked:boolean,blocked_reason:string,blocked_at:number}} ReportSchedule */
/** @typedef {{id:number,report_id:number,created_at:number,checksum:string,filename:string,destination:string,blocked:boolean,blocked_reason:string,blocked_at:number}} Delivery */
export {};
