// Mirror of backend us_states.py (Tax Foundation 2026). code, name, noTax.
export const US_STATES = [
  ["AL","Alabama"],["AK","Alaska",1],["AZ","Arizona"],["AR","Arkansas"],["CA","California"],
  ["CO","Colorado"],["CT","Connecticut"],["DE","Delaware"],["DC","Washington DC"],["FL","Florida",1],
  ["GA","Georgia"],["HI","Hawaii"],["ID","Idaho"],["IL","Illinois"],["IN","Indiana"],
  ["IA","Iowa"],["KS","Kansas"],["KY","Kentucky"],["LA","Louisiana"],["ME","Maine"],
  ["MD","Maryland"],["MA","Massachusetts"],["MI","Michigan"],["MN","Minnesota"],["MS","Mississippi"],
  ["MO","Missouri"],["MT","Montana"],["NE","Nebraska"],["NV","Nevada",1],["NH","New Hampshire",1],
  ["NJ","New Jersey"],["NM","New Mexico"],["NY","New York"],["NC","North Carolina"],["ND","North Dakota"],
  ["OH","Ohio"],["OK","Oklahoma"],["OR","Oregon"],["PA","Pennsylvania"],["RI","Rhode Island"],
  ["SC","South Carolina"],["SD","South Dakota",1],["TN","Tennessee",1],["TX","Texas",1],["UT","Utah"],
  ["VT","Vermont"],["VA","Virginia"],["WA","Washington",1],["WV","West Virginia"],["WI","Wisconsin"],["WY","Wyoming",1],
].map(([code, name, noTax]) => ({ code, name, noTax: !!noTax }));
