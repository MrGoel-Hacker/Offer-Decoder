export const regionFromPath = (path) => /^\/usa\/?$/.test(path) ? "us" : /^\/india\/?$/.test(path) ? "in" : null;
export const regionPath = (country) => country === "us" ? "/usa" : country === "in" ? "/india" : "/";
