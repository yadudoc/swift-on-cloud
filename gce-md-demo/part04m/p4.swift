type file;

(int result) randomInt ()
{
  float range = 9999999.0;
  float rand = java("java.lang.Math","random");
  string s[] = strsplit(toString(range*rand),"\\.");
  result = toInt(s[0]);
}

app (file out, file traj) simulation (string npart, string steps, string mass, file md)
{
  sh "-c chmod a+x md; ./md 3 " npart  steps "10 .0001" mass "0.1 1.0 0.2 0.05 50.0 0.1 2.5 2.0 " randomInt() @out @traj;
}

app (file o) analyze (file s[])
{
  mdstats filenames(s) stdout=filename(o);
}

app (file o) convert (file s[])
{
  convert filenames(s) filename(o);
}

int    nsim   = toInt(arg("nsim","10"));
string npart  = arg("npart","50");
string steps  = arg("steps","1000");
string mass   = arg("mass",".005");

file md <"md">;
file sim[] <simple_mapper; prefix="output/sim_", suffix=".out">;
file trj[] <simple_mapper; prefix="output/sim_", suffix=".trj.tgz">;

foreach i in [0:nsim-1] {
  (sim[i],trj[i]) = simulation(npart,steps,mass,md);
}

file stats_out<"output/average.out">;
stats_out = analyze(sim);

#file viz_all<"output/all.gif">;
#viz_all = convert(gifs);
