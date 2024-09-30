from typing import Union
from fastapi import FastAPI, Query, HTTPException, Response
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io

app = FastAPI()

# Load the data once when the server starts
df = pd.read_excel("Tickets_Filter_Modified.xlsx")

# Filter the data to exclude unreasonable processing times
perf_df = df[(df["Processing Duration"] > 0) & (df["Processing Duration"] < 240)]

# Compute the average processing time for each employee-service type pair
avg_processing_time = perf_df.groupby(["Accepted By", "Service Type"])["Processing Duration"].mean().unstack().fillna(float('inf'))

# Set matplotlib to use a non-interactive backend
plt.switch_backend('Agg')

@app.get("/recommend_employee")
def recommend_employee(service_type: str = Query(...)):
    if service_type not in avg_processing_time.columns:
        raise HTTPException(status_code=404, detail="Service type not found")
    
    # Find the employee with the minimum average processing time for the given service type
    recommended_employee = avg_processing_time[service_type].idxmin()
    min_processing_time = avg_processing_time[service_type].min()

    # In case multiple employees have the same minimum processing time, find all
    best_employees = avg_processing_time[avg_processing_time[service_type] == min_processing_time].index.tolist()

    return {
        "recommended_employee": recommended_employee,
        "min_processing_time": min_processing_time,
        "all_best_employees": best_employees
    }

@app.get("/emp_perf_taskwise")
def emp_perf_taskwise(emp_name: str = Query(...)):
    df_filtered = perf_df[(perf_df["Accepted By"] == emp_name)]

    if df_filtered.empty:
        raise HTTPException(status_code=404, detail="Employee not found")

    perf_df_grouped = df_filtered.groupby(["Accepted By", "Service Type"])["Processing Duration"].mean().unstack().fillna(0)
    
    plt.figure(figsize=(12, 10))
    sns.pointplot(x=perf_df_grouped.columns.tolist(), y=perf_df_grouped.loc[emp_name].tolist())
    for i in range(min(15, len(perf_df_grouped.loc[emp_name].tolist()))):
        plt.annotate(text=f'{int(perf_df_grouped.loc[emp_name].tolist()[i])}', xy=(i, int(perf_df_grouped.loc[emp_name].tolist()[i])),
                     textcoords="offset points", xytext=(-20, -8), ha='left')
    plt.xticks(rotation=90)
    plt.annotate(text="0 indicates no task performed", xy=(5, perf_df_grouped.loc[emp_name].max()))
    plt.ylabel("Processing Time in mins.")
    plt.title("Task Wise Performance of " + emp_name)
    
    perf_avg_df = perf_df.groupby(["Service Type"])["Processing Duration"].mean()
    sns.pointplot(x=perf_avg_df.index.tolist(), y=perf_avg_df.tolist(), color='red')
    for i in range(min(15, len(perf_avg_df.tolist()))):
        plt.annotate(text=f'{int(perf_avg_df.tolist()[i])}', xy=(i, int(perf_avg_df.tolist()[i])),
                     textcoords="offset points", ha='left', xytext=(0, 8))
    plt.tight_layout()

    # Save the plot to an in-memory buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # Clear the plot to avoid overlap with the next one
    plt.clf()

    return Response(content=buf.getvalue(), media_type="image/png")

@app.get("/")
def read_root():
    return {"Hello": "World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
